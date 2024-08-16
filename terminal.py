import os
import shutil
import curses
import zipfile
import tarfile
import difflib
import stat
from curses import wrapper

class FileExplorer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        self.current_path = os.path.expanduser("~")
        self.files = []
        self.selected = set()
        self.cursor = 0
        self.offset = 0

    def refresh(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        # Current path
        self.stdscr.addstr(0, 0, self.current_path, curses.color_pair(1))

        # File list
        self.files = sorted(os.listdir(self.current_path))
        for i in range(min(height - 3, len(self.files))):
            file = self.files[i + self.offset]
            if i + self.offset == self.cursor:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL
            if i + self.offset in self.selected:
                file = f"* {file}"
            self.stdscr.addstr(i + 1, 0, file[:width-1], mode)

        # Status bar
        status = f"Selected: {len(self.selected)} | Total: {len(self.files)}"
        self.stdscr.addstr(height - 1, 0, status.ljust(width), curses.color_pair(1))

        self.stdscr.refresh()

    def run(self):
        while True:
            self.refresh()
            key = self.stdscr.getch()

            if key == ord('q'):
                break
            elif key == curses.KEY_UP:
                self.cursor = max(0, self.cursor - 1)
            elif key == curses.KEY_DOWN:
                self.cursor = min(len(self.files) - 1, self.cursor + 1)
            elif key == ord(' '):
                if self.cursor in self.selected:
                    self.selected.remove(self.cursor)
                else:
                    self.selected.add(self.cursor)
            elif key == 10:  # Enter key
                self.open_item()
            elif key == ord('b'):
                self.go_back()
            elif key == ord('n'):
                self.create_folder()
            elif key == ord('d'):
                self.delete_item()
            elif key == ord('r'):
                self.rename_item()
            elif key == ord('c'):
                self.copy_item()
            elif key == ord('m'):
                self.move_item()
            elif key == ord('k'):
                self.bulk_operations()
            elif key == ord('p'):
                self.show_permissions()
            elif key == ord('z'):
                self.compress_items()
            elif key == ord('f'):
                self.filter_files()
            elif key == ord('e'):
                self.edit_text_file()
            elif key == ord('i'):
                self.file_diff()

    def open_item(self):
        item = self.files[self.cursor]
        item_path = os.path.join(self.current_path, item)
        if os.path.isdir(item_path):
            self.current_path = item_path
            self.cursor = 0
            self.offset = 0
            self.selected.clear()
        else:
            # Here you might want to use a file viewer or editor
            pass

    def go_back(self):
        self.current_path = os.path.dirname(self.current_path)
        self.cursor = 0
        self.offset = 0
        self.selected.clear()

    def create_folder(self):
        curses.echo()
        self.stdscr.addstr(0, 0, "Enter folder name: ")
        folder_name = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        new_folder_path = os.path.join(self.current_path, folder_name)
        try:
            os.mkdir(new_folder_path)
        except OSError:
            pass  # Handle error

    def delete_item(self):
        item = self.files[self.cursor]
        item_path = os.path.join(self.current_path, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
        except OSError:
            pass  # Handle error

    def rename_item(self):
        old_name = self.files[self.cursor]
        curses.echo()
        self.stdscr.addstr(0, 0, f"Enter new name for {old_name}: ")
        new_name = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        old_path = os.path.join(self.current_path, old_name)
        new_path = os.path.join(self.current_path, new_name)
        try:
            os.rename(old_path, new_path)
        except OSError:
            pass  # Handle error

    def copy_item(self):
        item = self.files[self.cursor]
        source_path = os.path.join(self.current_path, item)
        curses.echo()
        self.stdscr.addstr(0, 0, "Enter destination path: ")
        dest_path = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        try:
            if os.path.isdir(source_path):
                shutil.copytree(source_path, os.path.join(dest_path, item))
            else:
                shutil.copy2(source_path, dest_path)
        except OSError:
            pass  # Handle error

    def move_item(self):
        item = self.files[self.cursor]
        source_path = os.path.join(self.current_path, item)
        curses.echo()
        self.stdscr.addstr(0, 0, "Enter destination path: ")
        dest_path = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        try:
            shutil.move(source_path, dest_path)
        except OSError:
            pass  # Handle error

    def bulk_operations(self):
        items = [self.files[i] for i in self.selected]
        if not items:
            return

        curses.echo()
        self.stdscr.addstr(0, 0, "Choose operation (rename/copy/move/delete): ")
        operation = self.stdscr.getstr().decode('utf-8')
        curses.noecho()

        if operation == "rename":
            self.stdscr.addstr(0, 0, "Enter new name prefix: ")
            prefix = self.stdscr.getstr().decode('utf-8')
            for i, item in enumerate(items, 1):
                old_path = os.path.join(self.current_path, item)
                new_name = f"{prefix}_{i}{os.path.splitext(item)[1]}"
                new_path = os.path.join(self.current_path, new_name)
                try:
                    os.rename(old_path, new_path)
                except OSError:
                    pass  # Handle error
        elif operation in ["copy", "move"]:
            self.stdscr.addstr(0, 0, "Enter destination path: ")
            dest_path = self.stdscr.getstr().decode('utf-8')
            for item in items:
                source_path = os.path.join(self.current_path, item)
                try:
                    if operation == "copy":
                        if os.path.isdir(source_path):
                            shutil.copytree(source_path, os.path.join(dest_path, item))
                        else:
                            shutil.copy2(source_path, dest_path)
                    else:  # move
                        shutil.move(source_path, dest_path)
                except OSError:
                    pass  # Handle error
        elif operation == "delete":
            for item in items:
                item_path = os.path.join(self.current_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except OSError:
                    pass  # Handle error

        self.selected.clear()

    def show_permissions(self):
        item = self.files[self.cursor]
        item_path = os.path.join(self.current_path, item)
        perms = os.stat(item_path).st_mode
        perm_string = f"Owner: {'r' if perms & 0o400 else '-'}{'w' if perms & 0o200 else '-'}{'x' if perms & 0o100 else '-'}\n"
        perm_string += f"Group: {'r' if perms & 0o040 else '-'}{'w' if perms & 0o020 else '-'}{'x' if perms & 0o010 else '-'}\n"
        perm_string += f"Others: {'r' if perms & 0o004 else '-'}{'w' if perms & 0o002 else '-'}{'x' if perms & 0o001 else '-'}"
        
        self.stdscr.addstr(0, 0, f"Current permissions:\n{perm_string}\nEnter new permissions (e.g., 755): ")
        curses.echo()
        new_perms = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        if new_perms:
            try:
                os.chmod(item_path, int(new_perms, 8))
            except OSError:
                pass  # Handle error

    def compress_items(self):
        items = [self.files[i] for i in self.selected] if self.selected else [self.files[self.cursor]]
        
        self.stdscr.addstr(0, 0, "Choose format (zip/tar): ")
        curses.echo()
        compress_format = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        
        if compress_format in ["zip", "tar"]:
            self.stdscr.addstr(0, 0, "Enter archive name: ")
            curses.echo()
            archive_name = self.stdscr.getstr().decode('utf-8')
            curses.noecho()
            
            if compress_format == "zip":
                with zipfile.ZipFile(f"{archive_name}.zip", "w") as zipf:
                    for item in items:
                        item_path = os.path.join(self.current_path, item)
                        if os.path.isdir(item_path):
                            for root, _, files in os.walk(item_path):
                                for file in files:
                                    zipf.write(os.path.join(root, file), 
                                               os.path.relpath(os.path.join(root, file), self.current_path))
                        else:
                            zipf.write(item_path, item)
            else:  # tar
                with tarfile.open(f"{archive_name}.tar", "w") as tarf:
                    for item in items:
                        tarf.add(os.path.join(self.current_path, item), arcname=item)

    def filter_files(self):
        self.stdscr.addstr(0, 0, "Enter filter pattern (e.g., *.txt): ")
        curses.echo()
        filter_pattern = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        if filter_pattern:
            self.files = [item for item in os.listdir(self.current_path) 
                          if os.path.isdir(os.path.join(self.current_path, item)) or 
                          any(item.endswith(ext) for ext in filter_pattern.split(','))]
            self.cursor = 0
            self.offset = 0

    def edit_text_file(self):
        item = self.files[self.cursor]
        item_path = os.path.join(self.current_path, item)
        if os.path.isfile(item_path):
            curses.def_prog_mode()
            os.system(f'nano {item_path}')
            curses.reset_prog_mode()
            self.stdscr.refresh()

    def file_diff(self):
        self.stdscr.addstr(0, 0, "Enter path of first file: ")
        curses.echo()
        file1 = self.stdscr.getstr().decode('utf-8')
        self.stdscr.addstr(1, 0, "Enter path of second file: ")
        file2 = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        
        if file1 and file2:
            with open(file1, 'r') as f1, open(file2, 'r') as f2:
                diff = list(difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile=file1, tofile=file2))
            
            self.stdscr.clear()
            for i, line in enumerate(diff):
                if line.startswith('+'):
                    self.stdscr.addstr(i, 0, line, curses.color_pair(1))
                elif line.startswith('-'):
                    self.stdscr.addstr(i, 0, line, curses.color_pair(2))
                else:
                    self.stdscr.addstr(i, 0, line)
            self.stdscr.getch()

def main(stdscr):
    explorer = FileExplorer(stdscr)
    explorer.run()

wrapper(main)
