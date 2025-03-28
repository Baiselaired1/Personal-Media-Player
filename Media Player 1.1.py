import os               #PEP 8 style -- Standard library imports, third-party imports, specific/local imports
import sys
import contextlib
from math import floor
from setproctitle import setproctitle

import pygame
import vlc
 
setproctitle("Baise Media Player")



WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 500

class Button:
    def __init__(self, config):
        self.center_x = config.get('x', 0)
        self.center_y = config.get('y', 0)
        self.color = config.get('color', (100, 100, 200))
        self.hover_color = config.get('hover_color', (10, 10, 150))

        self.label = config.get('label', 'Click')
        self.label_color = config.get('label_color', (255, 255, 255))
        self.font = pygame.font.SysFont('Comic Sans', 16)

        text_size = self.font.size(self.label)          #size(x) returns a tuple of width, height, so we will use text_size to index them.
        self.width = text_size[0] + 20
        self.height = text_size[1] + 20

        self.rect = pygame.Rect(
            self.center_x - self.width//2,
            self.center_y - self.height//2,
            self.width,
            self.height
        )

        self.onClick = config.get('onClick', lambda: None)

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.check_mouse(mouse_pos) else self.color

        pygame.draw.rect(surface, color, self.rect)

        text_surface = self.font.render(self.label, True, self.label_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def check_mouse(self, mouse_pos):
        return self.rect.collidepoint(mouse_pos)

    def handle_click(self):
        if self.check_mouse(pygame.mouse.get_pos()):
            self.onClick()


class AudioManager:
    def __init__(self):
        try:
            self.instance = vlc.Instance('--quiet', '--no-video', '--no-video-title-show')
            self.player = self.instance.media_player_new()
            
            self.player.audio_set_volume(20)
        except Exception as error:
            print("VLC initialization failed: " + str(error))

    def play(self, track_path):
        try:
            current_volume = self.get_volume()

            self.player.set_media(self.instance.media_new(track_path))
            self.player.play()
            self.set_volume(current_volume)
        except Exception as error:
            raise Exception("Failed to play " + os.path.basename(track_path) + ": " + str(error))

    def stop(self):
        self.player.stop()

    def toggle_pause(self):
        self.player.pause()

    def get_volume(self):
        return self.player.audio_get_volume()
    
    def set_volume(self, volume):
        self.player.audio_set_volume(volume)
    
    def volume_raise(self, volume_raise_amount):
        current_volume = self.get_volume()
        new_volume = min(100, current_volume + volume_raise_amount)
        self.set_volume(new_volume)

    def volume_lower(self, volume_lower_amount):
        current_volume = self.get_volume()
        new_volume = max(0, current_volume - volume_lower_amount)
        self.set_volume(new_volume)

    def cleanup(self):
        self.player.stop()
        self.player.release()
        self.instance.release()
    
class RenderManager:
    MIN_WIDTH = 400
    MIN_HEIGHT = 200

    def __init__(self, audio_manager):
        pygame.init()
        pygame.font.init()

        self.audio_manager = audio_manager

        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        self.window = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Baise Media Player")

        self.font = pygame.font.SysFont('Comic Sans', 24)
        self.font_color = (255, 255, 255)

    def resize_window(self, event):
        set_screen_size = pygame.display.get_window_size()
        self.window_width = max(self.MIN_WIDTH, set_screen_size[0])
        self.window_height = max(self.MIN_HEIGHT, set_screen_size[1])
        self.window = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

        return True

    def render_song_info(self, title, artist, time_text, play_state):
        self.window.fill((0, 0, 0))

        if title:
            try:
                title_render = self.font.render(f"{title} (Paused)" if not play_state == vlc.State.Playing else f"{title}", True, self.font_color)
                title_rect = title_render.get_rect(center=(self.window_width//2, self.window_height * (1/4)))
                self.window.blit(title_render, title_rect)

                artist_render = self.font.render(artist, True, self.font_color)
                artist_render_rect = artist_render.get_rect(center=(self.window_width//2, self.window_height * (1/3)))
                self.window.blit(artist_render, artist_render_rect)

                time_render = self.font.render(time_text, True, self.font_color)
                time_rect = time_render.get_rect(center=(self.window_width//2, self.window_height * (1/2)))
                self.window.blit(time_render, time_rect)

                volume = self.audio_manager.get_volume()
                volume_render = self.font.render(str(volume) + "%", True, self.font_color)
                volume_rect = volume_render.get_rect(center=(self.window_width//2, self.window_height * (1/6)))
                self.window.blit(volume_render, volume_rect)

                status_text = "Playing" if play_state == vlc.State.Playing else "Paused"
                status_render = self.font.render(status_text, True, self.font_color)
                status_rect = status_render.get_rect(center=(self.window_width//2, self.window_height * (1/8)))
                self.window.blit(status_render, status_rect)
            except Exception as error:
                self.error_prompt_render("Error rendering song info: " + str(error), fatal=True)
        else:
            default_text_render = self.font.render("No song selected.", True, self.font_color)
            default_text_rect = default_text_render.get_rect(center=(self.window_width//2, self.window_height//2))
            self.window.blit(default_text_render, default_text_rect)
        
    def error_prompt_render(self, error_string, fatal=False):
        error_manager = ErrorManager(self.audio_manager)
        error_manager.error_render(error_string, fatal)

class ErrorManager:
    def __init__(self, audio_manager):
        self.audio_manager = audio_manager
        self.error_window = None
        self.error_queue = []           #Format of [(error_string, fatal), etc]
        self.error_active = False
        self.error_window_width = WINDOW_WIDTH * 4/5
        self.error_window_height = WINDOW_HEIGHT * 4/5

        self.error_font = pygame.font.SysFont('Comic Sans', 16)
        self.error_font_color = (255, 0, 0)

        self.running = True

        self.error_window = pygame.display.set_mode((self.error_window_width, self.error_window_height), pygame.RESIZABLE)
        pygame.display.set_caption("Error")

        self.soft_error_button = Button({
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

    def close_error(self):
        self.error_active = False

    def error_render(self, error_string, fatal):
        if self.error_active:
            self.error_queue.append((error_string, fatal))
            return
        
        self.error_active = True
        self.running = True
                    
        os.environ['SDL_VIDEO_WINDOW_POS'] = "100,100"
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
            pygame.display.set_caption("Media Player Script")
        
        self.error_active = False

        if self.error_queue:
            new_error_string, new_fatal = self.error_queue.pop(0)
            self.error_render(new_error_string, new_fatal)

    def error_text_render(self, error_string):
        lines = self._wrap_text(error_string, self.error_window_width - 20)
        heightBuffer = 30

        for line in lines:
            text_surface = self.error_font.render(line, True, self.error_font_color)
            text_rect = text_surface.get_rect(center=(self.error_window_width // 2, heightBuffer))
            self.error_window.blit(text_surface, text_rect)
            heightBuffer += 20

    def _wrap_text(self, text, max_width):
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

class PlaylistManager:
    def __init__(self, music_dir, render_manager, audio_manager):
        self.audio_manager = audio_manager
        self.render_manager = render_manager
        self.music_dir = music_dir
        self.tracks = []
        self.current_track = 0
        
        try:
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
    
    def get_current_track_path(self):
        return os.path.join(self.music_dir, self.tracks[self.current_track])

    def get_track_title(self):
        title = str(self.tracks[self.current_track])
        title = title.replace('.wav', '').replace('.mp3', '').replace('.ogg', '')
        return ' '.join(word.capitalize() for word in title.split('_'))
    
    def get_track_artist(self):
        return "Cam (PH4NT0MBexe)"
    
    def get_track_length(self):
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
        
    def get_track_information(self):
        if not self.tracks:
            return None

        return {
            'path': self.get_current_track_path(),
            'title': self.get_track_title(),
            'artist': self.get_track_artist(),
            'length': self.get_track_length()
        }
        
    def get_next_index(self):
        return (self.current_track + 1) % len(self.tracks)
    
    def get_previous_index(self):
        return (self.current_track - 1) % len(self.tracks)
    
    def advance(self):
        if not self.tracks:
            return None

        self.current_track = self.get_next_index()
        return self.get_current_track_path()
    
    def rewind(self):
        if not self.tracks:
            return None

        self.current_track = self.get_previous_index()
        return self.get_current_track_path()
        
    def get_formatted_time(self):
        if self.audio_manager.player.get_state() in [vlc.State.Playing, vlc.State.Paused]:
            try:
                current_time = self.audio_manager.player.get_time() // 1000
                total_time = self.audio_manager.player.get_length() // 1000
                
                current_min = int(current_time // 60)
                current_sec = int(current_time % 60)
                elapsed = f"{current_min}:{current_sec:02d}"

                total_min = int(total_time // 60)
                total_sec = int(total_time % 60)
                total = f"{total_min}:{total_sec:02d}"

                return f"{elapsed} / {total}"
            except Exception as error:
                self.render_manager.error_prompt_render("Error getting formatted time: " + str(error), fatal=True)
                return "00:00"
        
        return "00:00"

class MediaPlayer:
    def __init__(self):
        try:
            self.is_processing = False
            self.audio_manager = AudioManager()
            self.render_manager = RenderManager(self.audio_manager)
            self.playlist_manager = PlaylistManager(self.read_path(), self.render_manager, self.audio_manager)
            self.buttons_init()

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
        
    def read_path(self):
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

    def update_config(self):
        new_path = input("Enter the path to your music directory: ")
        with open('config.txt', 'w') as file:
            file.write(new_path)
        
        self.stop()
        self.playlist_manager = PlaylistManager(new_path, self.render_manager, self.audio_manager)

        if self.playlist_manager.tracks:
            track_path = self.playlist_manager.get_current_track_path()
            self.audio_manager.play(track_path)

        self.info_update()

    def stop(self):
        self.audio_manager.stop()

    def skip(self):
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

    def pause(self):
        self.audio_manager.toggle_pause()

    def progress(self):
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
    
    def rewind(self):
        with self.processing_lock() as processing:
            if not processing:
                return

            try:
                elapsed_time = self.audio_manager.player.get_time() // 1000
                self.stop()

                if elapsed_time < 5:
                    self.playlist_manager.rewind()
                    current_path = self.playlist_manager.get_current_track_path()
                    self.audio_manager.play(current_path)

                else:    
                    current_path = self.playlist_manager.get_current_track_path()
                    self.audio_manager.play(current_path)
            
                self.info_update()
            except Exception as error:
                self.render_manager.error_prompt_render("Rewind failed: " + str(error), fatal=False)
                return
        
    def quit(self):
        self.audio_manager.cleanup()
        pygame.quit()
        sys.exit()

    @contextlib.contextmanager
    def processing_lock(self):
        if self.is_processing:
            yield False
            return
        
        self.is_processing = True
        try:
            yield True
        finally:
            self.is_processing = False

    def info_update(self):
        if not self.playlist_manager.tracks:
            return

        self.render_manager.render_song_info(
            self.playlist_manager.get_track_title(),
            self.playlist_manager.get_track_artist(),
            self.playlist_manager.get_formatted_time(),
            self.audio_manager.player.get_state()
        )

    def buttons_init(self):
        self.buttons = {
        'pause_button': Button({
            'x': WINDOW_WIDTH * (1/4),
            'y': WINDOW_HEIGHT * (4/5),
            'label': "Pause",
            'onClick': lambda: self.pause()
        }),

        'skip_button': Button({
            'x': WINDOW_WIDTH * (2/4),
            'y': WINDOW_HEIGHT * (4/5),
            'label': "Skip",
            'onClick': lambda: self.skip()
        }),

        'rewind_button': Button({
            'x': WINDOW_WIDTH * (3/4),
            'y': WINDOW_HEIGHT * (4/5),
            'label': "Rewind",
            'onClick': lambda: self.rewind()
        }),

        'quit_button': Button({
            'x': WINDOW_WIDTH * (1/6),
            'y': WINDOW_HEIGHT * (1/2),
            'label': "Quit",
            'onClick': lambda: self.quit()
        })
    }
        
    def update(self):
        self.info_update()
        
        for button in self.buttons.values():
            button.draw(self.render_manager.window)
        
        pygame.display.flip()


def main():
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
                for button in media_player.buttons.values():
                    button.handle_click()
            elif event.type == pygame.VIDEORESIZE:
                media_player.render_manager.resize_window(event)
                media_player.buttons_init()
            
        media_player.update()
        media_player.progress()
        pygame.time.Clock().tick(60)

main()
