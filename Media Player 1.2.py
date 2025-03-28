import os
import sys
import contextlib

import pygame
import vlc



WINDOW_WIDTH = 1000                 #Window size constants
WINDOW_HEIGHT = 500

class Button:                                   #Button class, takes configs from inits in other classes or set by defaults
    def __init__(self, config):
        self.center_x = config.get('x', 0)
        self.center_y = config.get('y', 0)
        self.color = (10, 10, 200)
        self.hover_color = (100, 100, 150)

        self.label = config.get('label', 'Click')
        self.label_color = (255, 255, 255)
        self.font = pygame.font.SysFont('Comic Sans', 16)

        text_size = self.font.size(self.label)          #Size(x) returns a tuple of width, height, so we use text_size to index them.
        self.width = text_size[0] + 20
        self.height = text_size[1] + 20

        self.rect = pygame.Rect(
            self.center_x - self.width//2,
            self.center_y - self.height//2,
            self.width,
            self.height
        )

        self.onClick = config.get('onClick', lambda: None)

    def draw(self, surface):                        #Personal draw function
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.check_mouse(mouse_pos) else self.color

        pygame.draw.rect(surface, color, self.rect)

        text_surface = self.font.render(self.label, True, self.label_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def check_mouse(self, mouse_pos):                #Checks if mouse is hovering over button
        return self.rect.collidepoint(mouse_pos)

    def handle_click(self):                          #Checks if mouse is clicking on button
        if self.check_mouse(pygame.mouse.get_pos()):
            self.onClick()

class DragButton:                       #Parallel class to Button, but for drag buttons
    def __init__(self, config):
        self.name = config.get('name', 'button')
        self.center_x = config.get('x', 0)
        self.center_y = config.get('y', 0)
        self.radius = config.get('radius', 10)

        self.color = (10, 10, 200)
        self.dragging_color = (125, 50, 150)
        self.being_dragged = False

        self.min_x = config.get('min_x', 0)
        self.max_x = config.get('max_x', 100)

    def draw(self, surface):                    #Personal draw function
        color = self.dragging_color if self.being_dragged else self.color
        pygame.draw.circle(surface, color, (self.center_x, self.center_y + (self.radius//2)), self.radius)

    def check_mouse(self, mouse_pos):               #Checks if mouse is hovering over button
        return ((mouse_pos[0] - self.center_x) ** 2 + (mouse_pos[1] - self.center_y) ** 2) <= (self.radius ** 2)

    def handle_drag_start(self, mouse_pos):                 #Ran when button is both pressed and initially dragged
        if self.check_mouse(mouse_pos):
            self.being_dragged = True
            return True
        return False

    def handle_drag(self, mouse_pos):                 #Ran as button is dragged
        if self.being_dragged:
            new_x = max(self.min_x, min(self.max_x, mouse_pos[0]))
            self.center_x = new_x

            position_percent = (self.center_x - self.min_x) / (self.max_x - self.min_x)
            return position_percent
        return None

    def handle_drag_end(self):                 #Ran as button is released after being dragged
        if self.being_dragged:
            self.being_dragged = False
            position_percent = (self.center_x - self.min_x) / (self.max_x - self.min_x)
            return position_percent
        return None
    
    def update_pos(self, position_percent):             #Update position of button
        if self.being_dragged == False:
            self.center_x = self.min_x + (self.max_x - self.min_x) * position_percent

class AudioManager:                             #Class to handle vlc media playback and volume
    def __init__(self):                                 #Initialize VLC and player, set default volume
        try:
            self.instance = vlc.Instance('--quiet', '--no-video', '--no-video-title-show')
            self.player = self.instance.media_player_new()
            
            self.player.audio_set_volume(25)
        except Exception as error:
            print("VLC initialization failed: " + str(error))

    def play(self, track_path):                         #Store volume, create new media object and send to player, play and set volume
        try:
            current_volume = self.get_volume()

            self.player.set_media(self.instance.media_new(track_path))
            self.player.play()
            self.set_volume(current_volume)
        except Exception as error:
            raise Exception("Failed to play " + os.path.basename(track_path) + ": " + str(error))

    def stop(self):                                             #Stop player
        self.player.stop()

    def toggle_pause(self):                                     #Pause player -- Same function unpauses
        self.player.pause()
        
    def get_progress(self):                                     #Fetch player progress, returns tuple of current time and total time
        if self.player.get_state() in [vlc.State.Playing, vlc.State.Paused]:
            (current_time, total_time) = self.player.get_time() / 1000, self.player.get_length() / 1000

            if total_time <= 0:
                return (0, 0)

            return (current_time, total_time)

        return (0, 0)
    
    def set_progress(self, progress_percent):                   #Set player progress
        if self.player and progress_percent >= 0 and progress_percent <= 1:
            self.player.set_position(progress_percent)

    def get_volume(self):                                       #Fetch player volume
        return self.player.audio_get_volume()
    
    def set_volume(self, volume):                               #Set player volume
        self.player.audio_set_volume(volume)
    
    def volume_raise(self, volume_raise_amount):                #Raise volume by increment
        current_volume = self.get_volume()
        new_volume = min(100, current_volume + volume_raise_amount)
        self.set_volume(new_volume)

    def volume_lower(self, volume_lower_amount):                #Lower volume by increment
        current_volume = self.get_volume()
        new_volume = max(0, current_volume - volume_lower_amount)
        self.set_volume(new_volume)

    def cleanup(self):                                          #Stop and release player, release media instance
        self.player.stop()
        self.player.release()
        self.instance.release()
    
class RenderManager:                                #Class to handle pygame window and general rendering
    MIN_WIDTH = 400                                 #Minimum window size
    MIN_HEIGHT = 200

    def __init__(self, audio_manager):              #Initialize pygame, pygame font, and window -- Takes audio manager as a parameter to access player methods
        pygame.init()
        pygame.font.init()

        self.audio_manager = audio_manager

        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        self.window = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Baise Media Player")

        self.font = pygame.font.SysFont('Comic Sans', 24)
        self.font_color = (255, 255, 255)

    def resize_window(self):                         #Resize window, use as flag to update in main loop
        set_screen_size = pygame.display.get_window_size()
        self.window_width = max(self.MIN_WIDTH, set_screen_size[0])
        self.window_height = max(self.MIN_HEIGHT, set_screen_size[1])
        self.window = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        return True

    def render_song_info(self, title, artist, time_text, play_state):               #Render song info in title, artist, time, and volume -- default to no song selected
        self.window.fill((0, 0, 0))
        if title:
            try:
                volume = self.audio_manager.get_volume()

                title_render = self.font.render(f"{title} (Paused)" if not play_state == vlc.State.Playing else f"{title}", True, self.font_color)
                title_rect = title_render.get_rect(center=(self.window_width//2, self.window_height * (1/4)))
                self.window.blit(title_render, title_rect)

                artist_render = self.font.render(artist, True, self.font_color)
                artist_render_rect = artist_render.get_rect(center=(self.window_width//2, self.window_height * (1/3)))
                self.window.blit(artist_render, artist_render_rect)

                time_render = self.font.render(time_text, True, self.font_color)
                time_rect = time_render.get_rect(center=(self.window_width//2, self.window_height * (9/16)))
                self.window.blit(time_render, time_rect)

                volume_render = self.font.render(str(volume) + "%", True, self.font_color)
                volume_rect = volume_render.get_rect(center=(self.window_width//2, self.window_height * (1/6)))
                self.window.blit(volume_render, volume_rect)

            except Exception as error:
                self.error_prompt_render("Error rendering song info: " + str(error), fatal=True)
        else:
            default_text_render = self.font.render("No song selected.", True, self.font_color)
            default_text_rect = default_text_render.get_rect(center=(self.window_width//2, self.window_height//2))
            self.window.blit(default_text_render, default_text_rect)

    def volume_bar_render(self, volume):            #Render volume bar
        width = self.window_width * 0.1
        height = 10
        x = (self.window_width - width) // 2
        y = self.window_height * (1/10)

        pygame.draw.rect(self.window, (150, 100, 150), (x, y, width, height))
        pygame.draw.rect(self.window, (0, 0, 150), (x, y, (width * (volume / 100)), height))

    def progress_bar_render(self, progress):            #Render progress bar
        width = self.window_width * 0.6
        height = 10
        x = (self.window_width - width) // 2
        y = self.window_height * (5/8)

        pygame.draw.rect(self.window, (150, 100, 150), (x, y, width, height))
        pygame.draw.rect(self.window, (0, 0, 150), (x, y, (width * progress), height))

    def error_prompt_render(self, error_string, fatal=False):               #Method to call the error manager to render
        error_manager = ErrorManager(self.audio_manager)
        error_manager.error_render(error_string, fatal)

class ErrorManager:                                 #Class for exception handling and rendering, also takes audio manager as a parameter so it can properly run cleanup
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
        self.error_window = None
        self.error_queue = []                           #Format of [(error_string, fatal), etc], queue to prevent pileup with running flag to help iterate
        self.error_active = False
        self.error_window_width = WINDOW_WIDTH * 4/5
        self.error_window_height = WINDOW_HEIGHT * 4/5

        self.error_font = pygame.font.SysFont('Comic Sans', 16)
        self.error_font_color = (255, 0, 0)

        self.running = True

        self.error_window = pygame.display.set_mode((self.error_window_width, self.error_window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Error")

        self.soft_error_button = Button({                       #Button configurations, soft button returns to program, hard button exits
            'x': (self.error_window_width - 100)//2,
            'y': self.error_window_height - 50,
            'label': "Recover",
            'onClick': lambda: setattr(self, 'running', False)
        })

        self.hard_error_button = Button({
            'x': (self.error_window_width - 100)//2,
            'y': self.error_window_height - 50,
            'label': "Exit",
            'onClick': lambda: (
                self.audio_manager.cleanup(),
                pygame.quit(),
                sys.exit(1)
            )
        })

    def close_error(self):                  #Simple method to close current error
        self.error_active = False

    def error_render(self, error_string, fatal):        #Queues errors if one is already active, creates window and renders error, handles mouse clicks via buttons
        if self.error_active:
            self.error_queue.append((error_string, fatal))
            return
        
        self.error_active = True
        self.running = True
                    
        os.environ['SDL_VIDEO_WINDOW_POS'] = "100,100"              #Create a hard coded position for the error window
        self.error_window = pygame.display.set_mode((self.error_window_width, self.error_window_height))
        pygame.display.set_caption("Error")

        self.audio_manager.stop()
        current_button = self.hard_error_button if fatal else self.soft_error_button

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.hard_error_button.handle_click()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    current_button.handle_click()

            self.error_window.fill((0, 0, 0))
            current_button.draw(self.error_window)
            self.error_text_render(error_string)
            pygame.display.flip()
        
        if not fatal:
            pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
            pygame.display.set_caption("Baise Media Player")
        
        self.error_active = False

        if self.error_queue:                            #Recursive call to render next error in queue
            new_error_string, new_fatal = self.error_queue.pop(0)
            self.error_render(new_error_string, new_fatal)

    def error_text_render(self, error_string):                      #Render error text onto error window/button, sets wrap with a height margin
        lines = self._wrap_text(error_string, self.error_window_width - 20)
        heightBuffer = 30

        for line in lines:
            text_surface = self.error_font.render(line, True, self.error_font_color)
            text_rect = text_surface.get_rect(center=(self.error_window_width // 2, heightBuffer))
            self.error_window.blit(text_surface, text_rect)
            heightBuffer += 20

    def _wrap_text(self, text, max_width):                          #Method to wrap text with a width margin
        x_margin = 20
        effective_width = max_width - (x_margin * 2)

        words = text.split(' ')
        lines = []
        current_line = []
        current_width = 0

        for word in words:
            if current_width + len(word) + 1 <= effective_width:
                current_line.append(word)
                current_width += len(word) + 1
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_width = len(word) + 1
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

class PlaylistManager:                              #Class to handle track files and playlist management -- takes render manager and audio manager as parameters for error handling and info methods
    def __init__(self, music_dir, render_manager, audio_manager):
        self.audio_manager = audio_manager
        self.render_manager = render_manager
        self.music_dir = music_dir
        self.tracks = []
        self.current_track = 0
        
        try:                                    #Check directory/files exist, then for access, then supported file types
            if not os.path.exists(music_dir):
                self.render_manager.error_prompt_render(f"Directory missing: {music_dir}", fatal=True)
                return

            if not os.access(music_dir, os.R_OK):
                self.render_manager.error_prompt_render(f"Directory is not readable. Check you and this program have read access to: {music_dir}", fatal=True)
                return

            self.tracks = sorted([f for f in os.listdir(music_dir) if f.lower().endswith('.wav') or f.lower().endswith('.mp3') or f.lower().endswith('.ogg')])
            print(f"Playlist: {self.tracks}")

            if not self.tracks:
                self.render_manager.error_prompt_render(f"No supported tracks found in the specified directory. Supported file types are .wav, .mp3, and .ogg. Directory: {music_dir}", fatal=True)      #Maybe write a method to overwrite the config file?
            
        except Exception as error:
            self.render_manager.error_prompt_render("Playlist initialization failed: " + str(error), fatal=True)
    
    def get_current_track_path(self):                       #Returns current playlist index as a path
        return os.path.join(self.music_dir, self.tracks[self.current_track])

    def get_track_title(self):                              #Returns formatted title of current track
        title = str(self.tracks[self.current_track])
        title = title.replace('.wav', '').replace('.mp3', '').replace('.ogg', '')
        return ' '.join(word.capitalize() for word in title.split('_'))
    
    def get_track_artist(self):                             #Returns artist of current track (we only use tracks from Cam)
        return "Cam (PH4NT0MBexe)"
    
    def get_track_length(self):                             #Return length of current track, which involves a check for file corruption/compatibility
        try:
            track_path = self.get_current_track_path()
            media = self.audio_manager.instance.media_new(track_path)
            media.parse()
            if media.get_duration() < 0:                #Get duration can possibly return -1 if duration isn't ready
                return 0
            self.track_length = media.get_duration() / 1000
            return self.track_length
        except Exception as error:
            self.render_manager.error_prompt_render(f"Failed to get track length: {error}", fatal=True)
            return 0
        
    def get_track_information(self):                    #Returns a dictionary of track information using other info methods
        if not self.tracks:
            return None

        return {
            'path': self.get_current_track_path(),
            'title': self.get_track_title(),
            'artist': self.get_track_artist(),
            'length': self.get_track_length()
        }
        
    def get_next_index(self):                           #Returns next index in playlist
        return (self.current_track + 1) % len(self.tracks)
    
    def get_previous_index(self):                       #Returns previous index in playlist
        return (self.current_track - 1) % len(self.tracks)
    
    def advance(self):                                  #Advances playlist index and returns path to new current track file
        if not self.tracks:
            return None

        self.current_track = self.get_next_index()
        return self.get_current_track_path()
    
    def rewind(self):                                   #Rewinds playlist index and returns path to new current track file
        if not self.tracks:
            return None

        self.current_track = self.get_previous_index()
        return self.get_current_track_path()
        
    def get_formatted_time(self):                       #Returns formatted time of current track as elapsed / total
        if self.audio_manager.player.get_state() in [vlc.State.Playing, vlc.State.Paused]:
            try:
                (current_time, total_time) = self.audio_manager.get_progress()
                
                current_min = int(current_time // 60)
                current_sec = int(current_time % 60)
                elapsed = f"{current_min}:{current_sec:02d}"

                total_min = int(total_time // 60)
                total_sec = int(total_time % 60)
                total = f"{total_min}:{total_sec:02d}"

                return f"{elapsed} / {total}"
            except Exception as error:
                self.render_manager.error_prompt_render("Error getting formatted time: " + str(error), fatal=True)
                return "0:00 / 0:00"
        
        return "0:00 / 0:00"

class MediaPlayer:                  #Master class handling other classes, includes processing lock
    def __init__(self):             #Constructs other managers (error as part of render), initializes playlist, buttons, render info, and starts playing
        try:
            self.is_processing = False
            self.audio_manager = AudioManager()
            self.render_manager = RenderManager(self.audio_manager)
            self.playlist_manager = PlaylistManager(self.read_path(), self.render_manager, self.audio_manager)

            self.buttons = {}
            self.buttons_init()
            self.drag_buttons = {}
            self.drag_buttons_init()
            self.progress_drag = False

            if self.playlist_manager.tracks:
                track_path = self.playlist_manager.get_current_track_path()
                self.audio_manager.play(track_path)
                self.info_update()

        except Exception as error:
            if hasattr(self, 'render_manager'):
                self.render_manager.error_prompt_render("Player initialization failed: " + str(error), fatal=True)
            else:
                print("Critical error: Could not initialize render manager:", str(error))
                pygame.quit()
                sys.exit(1)
        
    def read_path(self):                        #Reads path from config file (will only make it here if playlist_manager proves file access)
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, 'config.txt')
            path = None
            
            if not os.path.exists(config_path):
                self.render_manager.error_prompt_render(f"Config file missing: {config_path}. Please create this config file with the path to your music directory.", fatal=True)
                return

            if not os.access(config_path, os.R_OK):
                self.render_manager.error_prompt_render(f"Config file is not readable. Check you and this program have read access to: {config_path}", fatal=True)
                return

            with open(config_path, 'r') as file:
                path = file.read().strip()
                return path
        except Exception as error:
            self.render_manager.error_prompt_render("Failed to read config file: " + str(error), fatal=True)

    def update_config(self):                        #Updates -- by overwriting -- config file and restarts playlist
        new_path = input("Enter the path to your music directory: ")
        with open('config.txt', 'w') as file:
            file.write(new_path)
        
        self.stop()
        self.playlist_manager = PlaylistManager(new_path, self.render_manager, self.audio_manager)

        if self.playlist_manager.tracks:
            track_path = self.playlist_manager.get_current_track_path()
            self.audio_manager.play(track_path)

        self.info_update()

    def stop(self):                                #Stop audio player
        self.audio_manager.stop()

    def skip(self):                                #Stop audio player, advance playlist, start new track, update info
        with self.processing_lock() as processing:
            if not processing:
                return

            try:
                self.stop()
                self.playlist_manager.advance()

                current_path = self.playlist_manager.get_current_track_path()
                self.audio_manager.play(current_path)

                self.info_update()
            except Exception as error:
                self.render_manager.error_prompt_render("Skip track failed: " + str(error), fatal=False)
                return

    def pause(self):                                #Toggle pause audio player
        self.audio_manager.toggle_pause()

    def progress(self):                             #Check if track has ended, if so, stop, advance playlist, start new track, update info
        with self.processing_lock() as processing:
            if not processing:
                return
        
            if self.audio_manager.player.get_state() == vlc.State.Ended:
                try:
                    self.stop()
                    self.playlist_manager.advance()

                    current_path = self.playlist_manager.get_current_track_path()
                    self.audio_manager.play(current_path)

                    self.info_update()
                except Exception as error:
                    self.render_manager.error_prompt_render("Failed to advance playlist: " + str(error), fatal=False)
                    return
    
    def rewind(self):                               #Check elapsed time, perform according rewind, update info
        with self.processing_lock() as processing:
            if not processing:
                return

            try:
                elapsed_time = self.audio_manager.get_progress()[0]
                self.stop()

                if elapsed_time < 5:              #If elapsed time is less than 5 seconds, rewind playlist
                    self.playlist_manager.rewind()
                    current_path = self.playlist_manager.get_current_track_path()
                    self.audio_manager.play(current_path)

                else:                            #If elapsed time is greater than 5 seconds, rewind track
                    current_path = self.playlist_manager.get_current_track_path()
                    self.audio_manager.play(current_path)
            
                self.info_update()
            except Exception as error:
                self.render_manager.error_prompt_render("Rewind failed: " + str(error), fatal=False)
                return
        
    def quit(self):                                 #Perform cleanup, quit pygame, exit program with normal/default flag
        self.audio_manager.cleanup()
        pygame.quit()
        sys.exit()

    @contextlib.contextmanager          #Context manager to lock processing, toggles based on is_processing state
    def processing_lock(self):
        if self.is_processing:
            yield False
            return
        
        self.is_processing = True
        try:
            yield True
        finally:
            self.is_processing = False

    def buttons_init(self):              #Initialize buttons and behaviors
        self.buttons = {
        'pause_button': Button({
            'x': self.render_manager.window_width * (1/4),
            'y': self.render_manager.window_height * (4/5),
            'label': "Pause",
            'onClick': lambda: self.pause()
        }),

        'skip_button': Button({
            'x': self.render_manager.window_width * (2/4),
            'y': self.render_manager.window_height * (4/5),
            'label': "Skip",
            'onClick': lambda: self.skip()
        }),

        'rewind_button': Button({
            'x': self.render_manager.window_width * (3/4),
            'y': self.render_manager.window_height * (4/5),
            'label': "Rewind",
            'onClick': lambda: self.rewind()
        }),

        'quit_button': Button({
            'x': self.render_manager.window_width * (1/6),
            'y': self.render_manager.window_height * (1/2),
            'label': "Quit",
            'onClick': lambda: self.quit()
        })
    }

    def drag_buttons_init(self):                    #Initialize drag buttons, behaviors are handled in following methods and inherent to their class
        progress_width = self.render_manager.window_width * 0.6
        progress_x = (self.render_manager.window_width - progress_width) // 2
        progress_y = self.render_manager.window_height * (5/8)

        volume_width = self.render_manager.window_width * 0.1
        volume_x = (self.render_manager.window_width - volume_width) // 2
        volume_y = self.render_manager.window_height * (1/10)

        self.drag_buttons = {
            'progress': DragButton({
                'name': 'progress',
                'x': progress_x,
                'y': progress_y,
                'radius': 10,
                'min_x': progress_x,
                'max_x': progress_x + progress_width
            }),

            'volume': DragButton({
                'name': 'volume',
                'x': volume_x + volume_width,
                'y': volume_y,
                'radius': 10,
                'min_x': volume_x,
                'max_x': volume_x + volume_width
            })
        }

    def handle_mouse_down(self, mouse_pos):                 #Program-wide mouse down handler
        for button in self.drag_buttons.values():
            if button.handle_drag_start(mouse_pos):
                return True

        for button in self.buttons.values():
            if button.check_mouse(mouse_pos):
                button.handle_click()
                return True

        return False
    
    def handle_mouse_up(self):                             #Program-wide mouse up handler
        results = {}

        for button in self.drag_buttons.values():
            position_percent = button.handle_drag_end()

            if position_percent is not None:
                results[button.name] = position_percent
        
        for button_name, position_percent in results.items():
            if button_name == 'progress':
                self.progress_drag = False
                self.audio_manager.set_progress(position_percent)
            elif button_name == 'volume':
                self.audio_manager.set_volume(int(position_percent * 100))
    
    def handle_mouse_motion(self, mouse_pos):                 #Program-wide mouse motion handler, only does things for the drag buttons and between trigger mouse events
        for button_name, button in self.drag_buttons.items():
            position_percent = button.handle_drag(mouse_pos)

            if position_percent is not None:
                if button_name == 'progress':
                    self.progress_drag = True

                elif button_name == 'volume':
                    self.render_manager.volume_bar_render(int(position_percent * 100))
                    self.audio_manager.set_volume(int(position_percent * 100))

    def info_update(self):                                 #Renders song info to window, called by other methods to update info
        if not self.playlist_manager.tracks:
            return

        self.render_manager.render_song_info(
            self.playlist_manager.get_track_title(),
            self.playlist_manager.get_track_artist(),
            self.playlist_manager.get_formatted_time(),
            self.audio_manager.player.get_state()
        )

    def update(self):                                  #Update render info and all buttons
        if not self.playlist_manager.tracks:
            return

        if self.audio_manager.player.get_state() in [vlc.State.Playing, vlc.State.Paused]:          #Confirm valid state or render blank progress bar
            (current_time, total_time) = self.audio_manager.get_progress()

            if total_time > 0:              #Check valid time, set time info or render blank progress bar
                progress = current_time / total_time
                self.drag_buttons['progress'].update_pos(progress)

                if self.progress_drag:                  #If progress button is being dragged, update time info accordingly, if not, update normally
                    drag_position = (self.drag_buttons['progress'].center_x - self.drag_buttons['progress'].min_x) / (self.drag_buttons['progress'].max_x - self.drag_buttons['progress'].min_x)
                    time_pass = f"{int(drag_position * total_time // 60)}:{int(drag_position * total_time % 60):02d} / {int(total_time // 60)}:{int(total_time % 60):02d}"

                    self.render_manager.render_song_info(
                        self.playlist_manager.get_track_title(),
                        self.playlist_manager.get_track_artist(),
                        time_pass,
                        self.audio_manager.player.get_state()
                    )

                    self.render_manager.progress_bar_render(drag_position)
                
                else:
                    self.info_update()
                    self.render_manager.progress_bar_render(progress)

            else:
                self.render_manager.progress_bar_render(0)

        else:
            self.render_manager.progress_bar_render(0)

        volume_percent = self.audio_manager.get_volume() / 100              #Update volume info in real time with drag position
        self.drag_buttons['volume'].update_pos(volume_percent)
        self.render_manager.volume_bar_render(self.audio_manager.get_volume())

        for button in self.drag_buttons.values():
            button.draw(self.render_manager.window)
        
        for button in self.buttons.values():
            button.draw(self.render_manager.window)
        
        pygame.display.flip()


def main():             #Create media player, run main loop for event handling, events are self explanatory, update and progress whenever possible
    media_player = MediaPlayer()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                media_player.quit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    media_player.pause()
                
                elif event.key == pygame.K_RIGHT:
                    media_player.skip()
                
                elif event.key == pygame.K_LEFT:
                    media_player.rewind()
                
                elif event.key == pygame.K_UP:
                    media_player.audio_manager.volume_raise(5)
                
                elif event.key == pygame.K_DOWN:
                    media_player.audio_manager.volume_lower(5)
                
                elif event.key == pygame.K_s:
                    media_player.stop()
                
                elif event.key == pygame.K_ESCAPE:
                    media_player.quit()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                media_player.handle_mouse_down(pygame.mouse.get_pos())
            
            elif event.type == pygame.MOUSEBUTTONUP:
                media_player.handle_mouse_up()
            
            elif event.type == pygame.MOUSEMOTION:
                media_player.handle_mouse_motion(pygame.mouse.get_pos())
            
            elif event.type == pygame.VIDEORESIZE:
                media_player.render_manager.resize_window()
                media_player.buttons_init()
                media_player.drag_buttons_init()
            
        media_player.update()
        media_player.progress()
        pygame.time.Clock().tick(30)            #Set framerate to 30 fps

main()              #Call main
