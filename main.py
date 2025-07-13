import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from ttkbootstrap import Style, Progressbar
from PIL import Image, ImageTk
import pydub
import numpy as np
import os
import random
import io
import threading
from pydub.playback import play
import warnings
from ttkbootstrap import Button
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

warnings.filterwarnings("ignore", category=RuntimeWarning)

class SongConverterApp:
    def __init__(self, root):
        self.root = root
        self.style = Style(theme='darkly')
        self.root.title("Nightcore Converter")
        self.root.geometry("500x600")
        self.song_path = ""
        self.cover_image = None
        self.progress = tk.DoubleVar(value=0)
        self.is_processing = False
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(main_frame, text="Select Song:").pack(pady=5)
        Button(main_frame, text="Browse MP3", 
               command=self.load_song, 
               bootstyle="outline").pack(pady=5)
        self.song_label = tk.Label(main_frame, text="No song selected")
        self.song_label.pack(pady=10)
        self.cover_frame = tk.Frame(main_frame, height=200, width=200, 
                                  relief=tk.SUNKEN, borderwidth=2)
        self.cover_frame.pack(pady=10)
        self.cover_frame.pack_propagate(False)
        self.cover_label = tk.Label(self.cover_frame)
        self.cover_label.pack(fill=tk.BOTH, expand=True)
        Button(main_frame, text="Add Cover Art", 
               command=self.add_cover_art,
               bootstyle="outline").pack(pady=5)
        self.progress_bar = Progressbar(main_frame, 
                                      variable=self.progress,
                                      maximum=100,
                                      bootstyle="success-striped")
        self.progress_bar.pack(fill=tk.X, pady=15)
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(pady=10)
        Button(btn_frame, text="Preview (15 sec)", 
               command=self.start_preview_thread,
               bootstyle="info-outline").pack(side=tk.LEFT, padx=5)
        Button(btn_frame, text="Export", 
               command=self.start_export_thread,
               bootstyle="success").pack(side=tk.LEFT, padx=5)
        
    def load_song(self):
        self.song_path = filedialog.askopenfilename(filetypes=[("MP3 Files", "*.mp3")])
        if self.song_path:
            self.song_label.config(text=os.path.basename(self.song_path))
            self.extract_cover_art()
            
    def extract_cover_art(self):
        try:
            audio = MP3(self.song_path, ID3=ID3)
            if audio.tags is not None:
                for tag in audio.tags.values():
                    if isinstance(tag, APIC):
                        image = Image.open(io.BytesIO(tag.data))
                        self.display_cover_image(image)
                        return
            self.cover_label.config(text="No cover art found", bg='gray20')
            self.cover_image = None
        except Exception as e:
            self.cover_label.config(text="Error loading cover", bg='gray20')
            
    def add_cover_art(self):
        if not self.song_path:
            messagebox.showwarning("Warning", "Please select a song first")
            return
        image_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.jpg *.jpeg *.png")])
        if image_path:
            try:
                image = Image.open(image_path)
                self.display_cover_image(image)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
                
    def display_cover_image(self, image):
        width, height = image.size
        max_size = 200
        ratio = min(max_size/width, max_size/height)
        new_size = (int(width*ratio), int(height*ratio))
        image = image.resize(new_size, Image.LANCZOS)
        self.cover_image = ImageTk.PhotoImage(image)
        self.cover_label.config(image=self.cover_image, text="")
        
    def apply_nightcore(self, audio_segment):
        self.update_progress(10)
        speed = 1.25
        new_sample_rate = int(audio_segment.frame_rate * speed)
        self.update_progress(30)
        nightcore = audio_segment._spawn(audio_segment.raw_data, overrides={
            'frame_rate': new_sample_rate
        })
        self.update_progress(60)
        nightcore = nightcore.set_frame_rate(audio_segment.frame_rate)
        self.update_progress(80)
        return nightcore
        
    def update_progress(self, value):
        self.progress.set(value)
        self.root.update_idletasks()
        
    def start_preview_thread(self):
        if self.is_processing:
            return
        threading.Thread(target=self.preview_song, daemon=True).start()
        
    def preview_song(self):
        if not self.song_path:
            messagebox.showwarning("Warning", "Please select a song first")
            return
        self.is_processing = True
        try:
            self.update_progress(5)
            audio = pydub.AudioSegment.from_file(self.song_path, format="mp3")
            self.update_progress(20)
            preview = self.apply_nightcore(audio)
            self.update_progress(80)
            preview[:15000].export("preview.mp3", format="mp3")
            self.update_progress(90)
            play(pydub.AudioSegment.from_file("preview.mp3"))
            self.update_progress(100)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create preview: {str(e)}")
        finally:
            self.is_processing = False
            self.update_progress(0)
            
    def start_export_thread(self):
        if self.is_processing:
            return
        threading.Thread(target=self.export_song, daemon=True).start()
        
    def export_song(self):
        if not self.song_path:
            messagebox.showwarning("Warning", "Please select a song first")
            return
        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 Files", "*.mp3")],
            initialfile=f"nightcore_{os.path.basename(self.song_path)}"
        )
        if not output_path:
            return
        self.is_processing = True
        try:
            self.update_progress(5)
            audio = pydub.AudioSegment.from_file(self.song_path, format="mp3")
            self.update_progress(20)
            converted = self.apply_nightcore(audio)
            self.update_progress(80)
            converted.export(output_path, format="mp3")
            self.update_progress(90)
            if hasattr(self, 'cover_image') and self.cover_image:
                img_data = io.BytesIO()
                img = ImageTk.getimage(self.cover_image)
                if img.mode in ("RGBA", "LA"):
                    img = img.convert("RGB")
                img.save(img_data, format='JPEG')
                img_data = img_data.getvalue()
                audiofile = MP3(output_path, ID3=ID3)
                try:
                    audiofile.add_tags()
                except error:
                    pass
                audiofile.tags.add(
                    APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3, desc=u'Cover',
                        data=img_data
                    )
                )
                audiofile.save()
            self.update_progress(100)
            messagebox.showinfo("Success", "Song exported successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export song: {str(e)}")
        finally:
            self.is_processing = False
            self.update_progress(0)

if __name__ == "__main__":
    root = tk.Tk()
    app = SongConverterApp(root)
    root.mainloop()