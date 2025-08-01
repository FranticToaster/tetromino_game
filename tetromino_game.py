import pygame,random,json
pygame.init()

class GameOverException(Exception):
    pass
class QuitGameException(Exception):
    pass

class Tetromino():
    def __init__(self,type_,gridpos,color,gravity_threshold,rotation_config,board):
        self.type=type_
        self.gridx,self.gridy=gridpos
        self.rotation=0
        self.color=color
        self.rotation_config=rotation_config

        self.__class__.square_size=30
        
        self.gravity_counter=0
        self.gravity_threshold=gravity_threshold

        if not self.is_legal_position(board):
            raise GameOverException
    @staticmethod
    def load_data(file_path):
        with open(file_path,"r") as json_file:
            return json.load(json_file)
    def is_legal_position(self,board):
        for y,row in enumerate(self.rotation_config[self.rotation]):
            for x,cell in enumerate(row):
                cell_x,cell_y=self.gridx+x,self.gridy+y
                if cell==1 and cell_y>=0:
                    if cell_x<0 or cell_x>=board.width or cell_y>=board.height or board.grid[cell_y][cell_x]!=None:
                        return False
        return True
    def rotate(self,direction,board):
        if direction=="clockwise":
            self.rotation=(self.rotation+1)%4
            if not self.is_legal_position(board):
                self.rotation=(self.rotation-1)%4
        elif direction=="anticlockwise":
            self.rotation=(self.rotation-1)%4
            if not self.is_legal_position(board):
                self.rotation=(self.rotation+1)%4
    def check_move_down_collision(self,board):
        for y,row in enumerate(self.rotation_config[self.rotation]):
            for x,cell in enumerate(row):
                if cell==1:
                    cell_x,cell_y=self.gridx+x,self.gridy+y
                    if cell_y+1>=board.height or board.grid[cell_y+1][cell_x]!=None:
                        return 1 #collision detected
        return 0 #no collision
    def paste_onto_board(self,board):
        for y,row in enumerate(self.rotation_config[self.rotation]):
            for x,cell in enumerate(row):
                if cell==1:
                    board.grid[self.gridy+y][self.gridx+x]=self.color
    def gravity(self,board):
        self.gravity_counter+=1
        if self.gravity_counter>=self.gravity_threshold:
            self.gravity_counter=0
            if self.check_move_down_collision(board):
                self.paste_onto_board(board)
                return 1 #signal to delete instance
            else:
                self.gridy+=1
                return 0
        return 0
    def draw(self,screen,margin):
        margin=max(2,margin-margin%2)
        for y,row in enumerate(self.rotation_config[self.rotation]):
            for x,cell in enumerate(row):
                if cell==1:
                    square_size=self.__class__.square_size
                    pygame.draw.rect(screen,self.color,pygame.Rect((self.gridx+x)*square_size+margin/2,(self.gridy+y)*square_size+margin/2,square_size-margin,square_size-margin))
    def update(self,screen,board,margin):
        delete_self=self.gravity(board)
        self.draw(screen,margin)
        return delete_self
    
class Board():
    def __init__(self,width=10,height=20):
        self.width=width
        self.height=height
        
        self.grid=[[None for _ in range(width)] for _ in range(height)]
    def draw_pieces(self,screen,margin):
        square_size=Tetromino.square_size
        for y,row in enumerate(self.grid):
            for x,cell in enumerate(row):
                if cell!=None:
                    pygame.draw.rect(screen,cell,pygame.Rect(x*square_size+margin/2,y*square_size+margin/2,square_size-margin,square_size-margin))
    def draw_board(self,screen,line_thickness):
        square_size=Tetromino.square_size
        for line in range(1,self.width+1):
            pygame.draw.line(screen,(255,255,255),(line*square_size,0),(line*square_size,square_size*self.height),width=line_thickness)
        for line in range(1,self.height+1):
            pygame.draw.line(screen,(255,255,255),(0,line*square_size),(square_size*self.width,line*square_size),width=line_thickness)
    def clear_lines(self):
        cleared_lines=0
        new_grid=[]

        for row in reversed(self.grid):
            if all(cell!=None for cell in row):
                cleared_lines+=1
            else:
                new_grid.insert(0,row) #keep the row

        #add empty rows
        for _ in range(cleared_lines):
            new_grid.insert(0,[None]*self.width)

        self.grid=new_grid
        return cleared_lines
    
    def update(self,screen,margin=2):
        margin=max(2,margin-margin%2)
        lines_cleared=self.clear_lines()
        self.draw_board(screen,margin)
        self.draw_pieces(screen,margin)
        return lines_cleared
class Game():
    def __init__(self,board,screen,starting_level=0,window_focused=False):
        self.board=board
        
        self.__class__.rotation_config=self.__class__.load_data("config/rotation_config.json")
        self.__class__.level_speeds=self.__class__.load_data("config/level_speeds.json")
        self.__class__.lines_to_score=self.__class__.load_data("config/lines_to_score.json")
        self.__class__.piece_colors=self.__class__.load_data("config/piece_colors.json")
        with open("config/highscore.txt","r") as highscore_file: 
            self.__class__.highscore=int(highscore_file.read())

        self.starting_level=starting_level
        self.level=self.starting_level
        self.next_piece_type=random.choice(("I","O","T","S","Z","J","L"))
        self.current_piece=self.spawn_piece()
        self.total_lines_cleared=0
        self.score=0
        self.das_direction=None
        self.das_counter=0
        self.down_key_pressed=False
        self.font1=pygame.font.SysFont("Arial",20)
        self.font2=pygame.font.SysFont("Arial",40)
        self.font2.set_bold(True)
        self.window_focused=window_focused
        self.paused=False

    @staticmethod
    def load_data(file_path):
        with open(file_path,"r") as json_file:
            return json.load(json_file)
    def spawn_piece(self):
        spawned_piece=Tetromino(self.next_piece_type,((self.board.width-4)//2,0),self.__class__.piece_colors[self.next_piece_type],self.__class__.level_speeds[self.level],self.__class__.rotation_config[self.next_piece_type],self.board)
        self.next_piece_type=random.choice(("I","O","T","S","Z","J","L"))
        return spawned_piece
    def handle_keydown_input(self,keyboard_input):
        if not self.paused:
            if keyboard_input==pygame.K_a or keyboard_input==pygame.K_LEFT:
                self.das_direction="left"
                self.das_counter=0
                if self.__class__.check_side_collision(self.current_piece,self.board) not in (1,3): #handle immediately
                    self.current_piece.gridx-=1
            elif keyboard_input==pygame.K_d or keyboard_input==pygame.K_RIGHT:
                self.das_direction="right"
                self.das_counter=0
                if self.__class__.check_side_collision(self.current_piece,self.board) not in (2,3): #handle immediately
                    self.current_piece.gridx+=1
            elif keyboard_input==pygame.K_s or keyboard_input==pygame.K_DOWN:
                self.down_key_pressed=True
            elif keyboard_input==pygame.K_z:
                self.current_piece.rotate("anticlockwise",self.board)
            elif keyboard_input==pygame.K_x:
                self.current_piece.rotate("clockwise",self.board)
            elif keyboard_input==pygame.K_ESCAPE:
                self.paused=True
        else:
            if keyboard_input==pygame.K_ESCAPE:
                self.paused=False
                self.das_direction=None
                self.das_counter=0
                self.down_key_pressed=False
    def handle_keyup_input(self,keyboard_input):
        if keyboard_input==pygame.K_a or keyboard_input==pygame.K_LEFT or keyboard_input==pygame.K_d or keyboard_input==pygame.K_RIGHT:
            self.das_direction=None
            self.das_counter=0
        elif keyboard_input==pygame.K_s or keyboard_input==pygame.K_DOWN:
            self.down_key_pressed=False
    @staticmethod
    def check_side_collision(current_piece,board):
        left_collision=right_collision=False
        for y,row in enumerate(current_piece.rotation_config[current_piece.rotation]):
            for x,cell in enumerate(row):
                if cell==1:
                    cell_x,cell_y=current_piece.gridx+x,current_piece.gridy+y
                    if cell_x<=0 or board.grid[cell_y][cell_x-1]!=None:
                        left_collision=True
                    if cell_x+1>=board.width or board.grid[cell_y][cell_x+1]!=None:
                        right_collision=True
        if left_collision and right_collision:
            return 3
        if left_collision:
            return 1
        if right_collision:
            return 2
        return 0 #no collision
    def handle_piece_movement(self):
        if (self.das_counter==16 or self.das_counter>16 and self.das_counter%6==4):
            if self.das_direction=="left" and self.__class__.check_side_collision(self.current_piece,self.board) not in (1,3):
                self.current_piece.gridx-=1
            if self.das_direction=="right" and self.__class__.check_side_collision(self.current_piece,self.board) not in (2,3):
                self.current_piece.gridx+=1
        if self.down_key_pressed:
            self.current_piece.gravity_threshold=min(2,self.current_piece.gravity_threshold)
        else:
            self.current_piece.gravity_threshold=self.__class__.level_speeds[self.level]
        self.das_counter+=1
    def should_level_up(self):
        if self.starting_level<10:
            return self.total_lines_cleared>=(self.level+1)*10
        else:
            lines_since_start=self.total_lines_cleared-self.starting_level*10
            return lines_since_start>=(self.level-self.starting_level+1)*10
    def draw(self,screen):
        screen_width=screen.get_width()
        
        lines_cleared_text_surface=self.font1.render(f"Lines cleared: {self.total_lines_cleared}",True,(255,255,255))
        score_text_surface=self.font1.render(f"Score: {self.score}",True,(255,255,255))
        highscore_text_surface=self.font1.render(f"Highscore: {self.__class__.highscore}",True,(255,255,255))
        level_text_surface=self.font1.render(f"Level: {self.level}",True,(255,255,255))

        y1=200
        screen.blit(lines_cleared_text_surface,(self.board.width*Tetromino.square_size+(screen_width-self.board.width*Tetromino.square_size-lines_cleared_text_surface.get_width())/2,200))
        y2=y1+lines_cleared_text_surface.get_height()
        screen.blit(score_text_surface,(self.board.width*Tetromino.square_size+(screen_width-self.board.width*Tetromino.square_size-score_text_surface.get_width())/2,y2))
        y3=y2+score_text_surface.get_height()
        screen.blit(highscore_text_surface,(self.board.width*Tetromino.square_size+(screen_width-self.board.width*Tetromino.square_size-highscore_text_surface.get_width())/2,y3))
        y4=y3+highscore_text_surface.get_height()
        screen.blit(level_text_surface,(self.board.width*Tetromino.square_size+(screen_width-self.board.width*Tetromino.square_size-level_text_surface.get_width())/2,y4))
    def draw_next_piece(self,screen,margin,line_thickness=4):
        margin=max(2,margin-margin%2)
        square_size=Tetromino.square_size
        gridx,gridy=self.board.width+1,2
        text_surface=self.font2.render("NEXT: ",True,(255,255,255))
        screen.blit(text_surface,(gridx*square_size,gridy*square_size-text_surface.get_height()))
        pygame.draw.rect(screen,(255,255,255),pygame.Rect(gridx*square_size,gridy*square_size,5*square_size,3*square_size),line_thickness)
        for y,row in enumerate(self.__class__.rotation_config[self.next_piece_type][0]):
            for x,cell in enumerate(row):
                if cell==1:
                    cell_x,cell_y=gridx+x+0.5,gridy+y+0.5
                    if self.next_piece_type not in ("I","O"):
                        cell_x+=0.5
                    pygame.draw.rect(screen,self.__class__.piece_colors[self.next_piece_type],pygame.Rect(cell_x*square_size+margin/2,cell_y*square_size+margin/2,square_size-margin,square_size-margin))
    def draw_pause_screen(self,screen):
        text_surface=self.font2.render("PAUSED",True,(90,150,255))
        screen.blit(text_surface,((screen.get_width()-text_surface.get_width())/2,(screen.get_height()-text_surface.get_height())/2))
    def handle_window_focus(self,event_type):
        if event_type==pygame.WINDOWFOCUSGAINED:
            self.window_focused=True
        elif event_type==pygame.WINDOWFOCUSLOST:
            self.window_focused=False
    def update(self,screen,margin=2):
        if (not self.paused) and self.window_focused:
            self.handle_piece_movement()
            lines_cleared=self.board.update(screen,margin)
            if lines_cleared>0:
                self.score+=self.__class__.lines_to_score[str(lines_cleared)]*(self.level+1)
                self.total_lines_cleared+=lines_cleared
                if self.should_level_up():
                    self.level+=1
                if self.score>self.__class__.highscore:
                    self.__class__.highscore=self.score
                    with open("config/highscore.txt","w") as highscore_file:
                        highscore_file.write(str(self.score))
            if bool(self.current_piece.update(screen,self.board,margin)):
                self.current_piece=self.spawn_piece()
            self.draw(screen)
            self.draw_next_piece(screen,margin)
        else:
            self.draw_pause_screen(screen)

class Play_again_button():
    def __init__(self,x,y,width,height,color1,color2,*text_info):
        self.x=x
        self.y=y
        self.width=width
        self.height=height
        self.rect=pygame.Rect(self.x,self.y,self.width,self.height)
        self.color1=color1 #different color when hovered
        self.color2=color2
        self.text,self.text_color,font,font_size=tuple(zip(*text_info))
        self.font=[pygame.font.SysFont(i,j) for i,j in zip(font,font_size)]
        self.isHovered=False
        self.wasClicked=False
    def draw(self,screen):
        if self.isHovered:
            pygame.draw.rect(screen,self.color2,self.rect)
        else:
            pygame.draw.rect(screen,self.color1,self.rect)
    def draw_text(self,screen):
        image_surface=[self.font[i].render(self.text[i],True,self.text_color[i]) for i in range(len(self.text))]
        total_text_height=sum(i.get_height() for i in image_surface)
        for i in range(len(self.text)):
            x_margin=(self.width-image_surface[i].get_width())/2
            y_margin=(self.height-total_text_height)/2+sum(j.get_height() for j in image_surface[:i])
            screen.blit(image_surface[i],(self.x+x_margin,self.y+y_margin))
    def handle_mouse_interactions(self):
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            self.isHovered=True
            if pygame.mouse.get_pressed()[0]:
                self.wasClicked=True
        else:
            self.isHovered=False
    def update(self,screen):
        self.handle_mouse_interactions()
        self.draw(screen)
        self.draw_text(screen)

class State_machine():
    def __init__(self):
        self.current_state=None
    def change_state(self,new_state,enter_args=(),enter_kwargs={},exit_args=(),exit_kwargs={}):
        if self.current_state!=None:
            self.current_state.exit(*exit_args,**exit_kwargs)
        self.current_state=new_state
        self.current_state.enter(*enter_args,**enter_kwargs)
    def update(self,*args,**kwargs):
        if self.current_state!=None:
            self.current_state.update(*args,**kwargs)

class State():
    def enter(self):
        pass
    def exit(self):
        pass
    def update(self):
        pass

class Playing_game_state(State):
    def enter(self,*args,**kwargs):
        self.screen=kwargs["screen"]
        self.state_machine=kwargs["state_machine"]
        self.clock=kwargs["clock"]
        self.starting_level=kwargs["starting_level"]
        board=Board()
        self.game=Game(board,self.screen,self.starting_level,window_focused=kwargs["window_focused"])
    def exit(self,*args,**kwargs):
        pass
    def update(self,*args,**kwargs):
        self.clock.tick(60)
        self.screen.fill((0,0,0))
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                raise QuitGameException
            elif event.type==pygame.KEYDOWN:
                self.game.handle_keydown_input(event.key)
            elif event.type==pygame.KEYUP:
                self.game.handle_keyup_input(event.key)
            elif event.type==pygame.WINDOWFOCUSLOST or event.type==pygame.WINDOWFOCUSGAINED:
                self.game.handle_window_focus(event.type)
                
        try:       
            self.game.update(self.screen)
        except GameOverException:
            self.state_machine.change_state(Play_again_state(),enter_kwargs={"screen":self.screen,"state_machine":self.state_machine,"clock":self.clock,"starting_level":self.starting_level})
        
        pygame.display.update()
        
class Play_again_state(State):
    def enter(self,*args,**kwargs):
        self.screen=kwargs["screen"]
        self.state_machine=kwargs["state_machine"]
        self.clock=kwargs["clock"]
        self.starting_level=kwargs["starting_level"]
        width,height=(200,80)
        self.button=Play_again_button((self.screen.get_width()-width)/2,(self.screen.get_height()-height)/2,width,height,(0,255,255),(255,0,0),(("Play Again",(0,0,0),None,30)))
    def exit(self,*args,**kwargs):
        pass
    def update(self,*args,**kwargs):
        self.clock.tick(60)
        self.screen.fill((0,0,0))
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                raise QuitGameException

        self.button.update(self.screen)
        if self.button.wasClicked:
            self.state_machine.change_state(Playing_game_state(),enter_kwargs={"screen":self.screen,"state_machine":self.state_machine,"clock":self.clock,"starting_level":self.starting_level,"window_focused":True})
        
        pygame.display.update()
def main():
    try:
        starting_level=int(input("Starting level: "))
        if starting_level>19:
            starting_level=0
    except ValueError:
        starting_level=0
    
    screen_width,screen_height=(600,600)
    screen=pygame.display.set_mode((screen_width,screen_height))

    state_machine=State_machine()
    
    clock=pygame.time.Clock()
    state_machine.change_state(Playing_game_state(),enter_kwargs={"screen":screen,"state_machine":state_machine,"clock":clock,"starting_level":starting_level,"window_focused":False})
        
    while True:
        try:
            state_machine.update()
        except QuitGameException:
            break
    pygame.quit()

if __name__=="__main__":
    main()

