import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import xml.etree.ElementTree as ET
import os
import sys
import subprocess
import requests
import zipfile
import shutil
from threading import Thread
import time

class CraftGameLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("CraftGame Launcher")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.versions_xml = os.path.join(self.base_dir, "versions.xml")
        self.installed_xml = os.path.join(self.base_dir, "installed.xml")
        self.versions_dir = os.path.join(self.base_dir, "versions")
        
        if not os.path.exists(self.versions_dir):
            os.makedirs(self.versions_dir)
        self.available_versions = self.load_available_versions()
        self.installed_versions = self.load_installed_versions()
        
        self.create_widgets()
        
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        title_label = ttk.Label(main_frame, text="CraftGame Launcher", 
                                font=("Arial", 24, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        version_label = ttk.Label(main_frame, text="Версия игры:", font=("Arial", 12))
        version_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.version_var = tk.StringVar()
        versions_list = [v['name'] for v in self.available_versions]
        self.version_combo = ttk.Combobox(main_frame, textvariable=self.version_var, 
                                         values=versions_list, state="readonly", width=30)
        if versions_list:
            self.version_combo.current(0)
        self.version_combo.grid(row=1, column=1, pady=5, padx=(10, 0))
        
        self.install_btn = ttk.Button(main_frame, text="Установить", 
                                     command=self.install_version, width=15)
        self.install_btn.grid(row=1, column=2, pady=5, padx=(10, 0))
        
        self.my_versions_btn = ttk.Button(main_frame, text="Мои Версии", 
                                         command=self.show_my_versions, width=15)
        self.my_versions_btn.grid(row=2, column=0, columnspan=3, pady=(20, 10))
        
        self.start_btn = ttk.Button(main_frame, text="Начать", 
                                   command=self.start_game, width=30)
        self.start_btn.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self.progress.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.status_label = ttk.Label(main_frame, text="Готов к работе", 
                                      font=("Arial", 9))
        self.status_label.grid(row=5, column=0, columnspan=3, pady=5)
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def load_available_versions(self):
        versions = []
        try:
            if os.path.exists(self.versions_xml):
                tree = ET.parse(self.versions_xml)
                root = tree.getroot()
                for version in root.findall('version'):
                    name = version.find('name').text
                    url = version.find('url').text
                    versions.append({'name': name, 'url': url})
        except Exception as e:
            print(f"Ошибка загрузки versions.xml: {e}")
        return versions
    
    def load_installed_versions(self):
        versions = []
        try:
            if os.path.exists(self.installed_xml):
                tree = ET.parse(self.installed_xml)
                root = tree.getroot()
                for version in root.findall('installed_version'):
                    name = version.find('name').text
                    folder = version.find('folder').text
                    versions.append({'name': name, 'folder': folder})
        except Exception as e:
            print(f"Ошибка загрузки installed.xml: {e}")
        return versions
    
    def save_installed_version(self, version_name, version_folder):
        try:
            if os.path.exists(self.installed_xml):
                tree = ET.parse(self.installed_xml)
                root = tree.getroot()
            else:
                root = ET.Element("installed_versions")
                tree = ET.ElementTree(root)
            
            version_elem = ET.SubElement(root, "installed_version")
            name_elem = ET.SubElement(version_elem, "name")
            name_elem.text = version_name
            folder_elem = ET.SubElement(version_elem, "folder")
            folder_elem.text = version_folder
            
            tree.write(self.installed_xml, encoding='UTF-8', xml_declaration=True)
        except Exception as e:
            print(f"Ошибка сохранения installed.xml: {e}")
    
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update()
    
    def download_file(self, url, destination):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(destination, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            self.update_status(f"Скачивание: {percent:.1f}%")
            
            return True
        except Exception as e:
            self.update_status(f"Ошибка скачивания: {e}")
            return False
    
    def install_version(self):
        selected_version = self.version_var.get()
        if not selected_version:
            messagebox.showwarning("Предупреждение", "Выберите версию для установки")
            return
        
        version_info = None
        for v in self.available_versions:
            if v['name'] == selected_version:
                version_info = v
                break
        
        if not version_info:
            messagebox.showerror("Ошибка", "Версия не найдена")
            return
        
        for installed in self.installed_versions:
            if installed['name'] == selected_version:
                messagebox.showinfo("Информация", "Эта версия уже установлена")
                return
        
        thread = Thread(target=self._install_version_thread, args=(version_info,))
        thread.daemon = True
        thread.start()
    
    def _install_version_thread(self, version_info):
        self.install_btn.config(state='disabled')
        self.start_btn.config(state='disabled')
        self.progress.start()
        
        try:
            version_name = version_info['name']
            version_url = version_info['url']
            
            temp_zip = os.path.join(self.versions_dir, "dist.zip")
            final_zip = os.path.join(self.versions_dir, f"{version_name}.zip")
            version_folder = os.path.join(self.versions_dir, version_name)
            
            self.update_status(f"Скачивание {version_name}...")
            if not self.download_file(version_url, temp_zip):
                return
            
            self.update_status("Переименование файла...")
            if os.path.exists(final_zip):
                os.remove(final_zip)
            os.rename(temp_zip, final_zip)
            
            self.update_status("Распаковка архива...")
            if os.path.exists(version_folder):
                shutil.rmtree(version_folder)
            os.makedirs(version_folder)
            
            with zipfile.ZipFile(final_zip, 'r') as zip_ref:
                zip_ref.extractall(version_folder)

            self.update_status("Очистка...")
            os.remove(final_zip)
            
            self.save_installed_version(version_name, version_name)
            
            self.installed_versions.append({'name': version_name, 'folder': version_name})
            
            self.update_status(f"Установка {version_name} завершена!")
            messagebox.showinfo("Успех", f"Версия {version_name} успешно установлена!")
            
        except Exception as e:
            self.update_status(f"Ошибка установки: {e}")
            messagebox.showerror("Ошибка", f"Не удалось установить версию: {e}")
        finally:
            self.progress.stop()
            self.install_btn.config(state='normal')
            self.start_btn.config(state='normal')
    
    def show_my_versions(self):
        if not self.installed_versions:
            messagebox.showinfo("Мои версии", "У вас нет установленных версий")
            return
        
        versions_window = tk.Toplevel(self.root)
        versions_window.title("Мои версии")
        versions_window.geometry("400x300")
        versions_window.resizable(False, False)
        
        versions_window.transient(self.root)
        versions_window.grab_set()
        
        frame = ttk.Frame(versions_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        label = ttk.Label(frame, text="Установленные версии:", font=("Arial", 12, "bold"))
        label.pack(pady=(0, 10))
        
        listbox = tk.Listbox(frame, height=10, font=("Arial", 10))
        listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        for version in self.installed_versions:
            listbox.insert(tk.END, version['name'])
        
        def launch_selected():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                version_name = self.installed_versions[index]['name']
                versions_window.destroy()
                self.launch_version(version_name)
            else:
                messagebox.showwarning("Предупреждение", "Выберите версию для запуска")
        
        launch_btn = ttk.Button(frame, text="Запустить", command=launch_selected)
        launch_btn.pack()
    
    def start_game(self):
        if not self.installed_versions:
            messagebox.showwarning("Предупреждение", "У вас нет установленных версий")
            return
        
        last_version = self.installed_versions[-1]['name']
        self.launch_version(last_version)
    
    def launch_version(self, version_name):
        version_info = None
        for v in self.installed_versions:
            if v['name'] == version_name:
                version_info = v
                break
        
        if not version_info:
            messagebox.showerror("Ошибка", "Версия не найдена")
            return
        
        version_folder = os.path.join(self.versions_dir, version_info['folder'])
        exe_path = os.path.join(version_folder, "CraftGame.exe")
        
        if not os.path.exists(exe_path):
            messagebox.showerror("Ошибка", f"Не найден файл CraftGame.exe в папке {version_name}")
            return
        
        try:
            self.update_status(f"Запуск {version_name}...")
            subprocess.Popen([exe_path], cwd=version_folder)
            self.update_status("Игра запущена")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить игру: {e}")
            self.update_status("Ошибка запуска")

def main():
    root = tk.Tk()
    app = CraftGameLauncher(root)
    root.mainloop()

if __name__ == "__main__":
    main()