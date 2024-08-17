import os
import shutil
import curses
import zipfile
import tarfile
import difflib
import stat
import datetime
from curses import wrapper

class FileExplorer:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_GREEN)  # Status bar and top bar
        curses.init_pair(2, curses.COLOR_BLUE, -1)   # Directories
        curses.init_pair(3, curses.COLOR_RED, -1)    # Executables
        curses.init_pair(4, curses.COLOR_WHITE, -1)  # Regular files
        curses.init_pair(5, curses.COLOR_YELLOW, -1) # Symlinks
        self.current_path = os.path.expanduser("~")
        self.files = []
        self.selected = set()
        self.cursor = 0
        self.offset = 0
        self.sort_key = "name"
        self.reverse_sort = False

    def refresh(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()

        # Top bar
        self.stdscr.addstr(0, 0, self.current_path[:width-1].ljust(width-1), curses.color_pair(1))

        # File list
        self.files = self.get_sorted_files()
        for i in range(min(height - 3, len(self.files))):
            file = self.files[i + self.offset]
            file_path = os.path.join(self.current_path, file)
            if i + self.offset == self.cursor:
                mode = curses.A_REVERSE
            else:
                mode = curses.A_NORMAL
            if i + self.offset in self.selected:
                file = f"* {file}"
            file_display = file[:width-1]
            
            color_pair = curses.color_pair(4)  # Default to regular file color
            if file == "..":
                color_pair = curses.color_pair(2)  # Use directory color for ".."
            elif os.path.isdir(file_path):
                color_pair = curses.color_pair(2)
            elif os.access(file_path, os.X_OK):
                color_pair = curses.color_pair(3)
            elif os.path.islink(file_path):
                color_pair = curses.color_pair(5)
            
            self.stdscr.addstr(i + 1, 0, file_display, color_pair | mode)

        # Status bar
        status = f"Selected: {len(self.selected)} | Total: {len(self.files)} | Sort: {self.sort_key} ({'Desc' if self.reverse_sort else 'Asc'})"
        keys = "q:Quit | Enter:Open | Space:Select | n:New | d:Delete | r:Rename | c:Copy | m:Move | k:Bulk | p:Perms | z:Zip | f:Filter | e:Edit | i:Diff | s:Sort | h:Help"
        status_display = f"{status} | {keys}"[:width-1]
        self.stdscr.addstr(height - 1, 0, status_display.ljust(width-1), curses.color_pair(1))

        self.stdscr.refresh()

    def get_sorted_files(self):
        files = [".."] + os.listdir(self.current_path)
        if self.sort_key == "name":
            return [".."] + sorted(files[1:], key=lambda x: x.lower(), reverse=self.reverse_sort)
        elif self.sort_key == "size":
            return [".."] + sorted(files[1:], key=lambda x: os.path.getsize(os.path.join(self.current_path, x)), reverse=self.reverse_sort)
        elif self.sort_key == "date":
            return [".."] + sorted(files[1:], key=lambda x: os.path.getmtime(os.path.join(self.current_path, x)), reverse=self.reverse_sort)
        elif self.sort_key == "type":
            return [".."] + sorted(files[1:], key=lambda x: os.path.splitext(x)[1], reverse=self.reverse_sort)

    def run(self):
        while True:
            try:
                self.refresh()
                key = self.stdscr.getch()

                if key == ord('q'):
                    break
                elif key == curses.KEY_UP:
                    self.cursor = max(0, self.cursor - 1)
                elif key == curses.KEY_DOWN:
                    self.cursor = min(len(self.files) - 1, self.cursor + 1)
                elif key == ord(' '):
                    if self.cursor != 0:  # Prevent selecting ".."
                        if self.cursor in self.selected:
                            self.selected.remove(self.cursor)
                        else:
                            self.selected.add(self.cursor)
                elif key == 10:  # Enter key
                    self.open_item()
                elif key == ord('b'):
                    self.go_back()
                elif key == ord('n'):
                    self.create_item()
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
                elif key == ord('s'):
                    self.change_sort()
                elif key == ord('h'):
                    self.show_help()

            except Exception as e:
                self.stdscr.clear()
                self.stdscr.addstr(0, 0, f"An error occurred: {str(e)}", curses.color_pair(1))
                self.stdscr.addstr(1, 0, "Press any key to continue...", curses.color_pair(1))
                self.stdscr.refresh()
                self.stdscr.getch()

    def open_item(self):
        item = self.files[self.cursor]
        if item == "..":
            self.go_back()
        else:
            item_path = os.path.join(self.current_path, item)
            if os.path.isdir(item_path):
                self.current_path = item_path
                self.cursor = 0
                self.offset = 0
                self.selected.clear()
            else:
                # Open file with default application
                curses.def_prog_mode()
                os.system(f'xdg-open "{item_path}"')
                curses.reset_prog_mode()
                self.stdscr.refresh()

    def go_back(self):
        self.current_path = os.path.dirname(self.current_path)
        self.cursor = 0
        self.offset = 0
        self.selected.clear()

    def create_item(self):
        curses.echo()
        self.stdscr.addstr(0, 0, "Enter item name (end with / for directory): ", curses.color_pair(1))
        item_name = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        new_item_path = os.path.join(self.current_path, item_name)
        try:
            if item_name.endswith('/'):
                os.mkdir(new_item_path)
            else:
                open(new_item_path, 'a').close()
        except OSError:
            pass  # Handle error

    def delete_item(self):
        item = self.files[self.cursor]
        if item == "..":
            return
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
        if old_name == "..":
            return
        curses.echo()
        self.stdscr.addstr(0, 0, f"Enter new name for {old_name}: ", curses.color_pair(1))
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
        if item == "..":
            return
        source_path = os.path.join(self.current_path, item)
        curses.echo()
        self.stdscr.addstr(0, 0, "Enter destination path: ", curses.color_pair(1))
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
        if item == "..":
            return
        source_path = os.path.join(self.current_path, item)
        curses.echo()
        self.stdscr.addstr(0, 0, "Enter destination path: ", curses.color_pair(1))
        dest_path = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        try:
            shutil.move(source_path, dest_path)
        except OSError:
            pass  # Handle error

    def bulk_operations(self):
        items = [self.files[i] for i in self.selected if self.files[i] != ".."]
        if not items:
            return

        curses.echo()
        self.stdscr.addstr(0, 0, "Choose operation (rename/copy/move/delete): ", curses.color_pair(1))
        operation = self.stdscr.getstr().decode('utf-8')
        curses.noecho()

        if operation == "rename":
            self.stdscr.addstr(0, 0, "Enter new name prefix: ", curses.color_pair(1))
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
            self.stdscr.addstr(0, 0, "Enter destination path: ", curses.color_pair(1))
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
        if item == "..":
            return
        item_path = os.path.join(self.current_path, item)
        perms = os.stat(item_path).st_mode
        perm_string = f"Owner: {'r' if perms & 0o400 else '-'}{'w' if perms & 0o200 else '-'}{'x' if perms & 0o100 else '-'}\n"
        perm_string += f"Group: {'r' if perms & 0o040 else '-'}{'w' if perms & 0o020 else '-'}{'x' if perms & 0o010 else '-'}\n"
        perm_string += f"Others: {'r' if perms & 0o004 else '-'}{'w' if perms & 0o002 else '-'}{'x' if perms & 0o001 else '-'}"
        
        self.stdscr.addstr(0, 0, f"Current permissions:\n{perm_string}\nEnter new permissions (e.g., 755): ", curses.color_pair(1))
        curses.echo()
        new_perms = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        if new_perms:
            try:
                os.chmod(item_path, int(new_perms, 8))
            except OSError:
                pass  # Handle error

    def compress_items(self):
        items = [self.files[i] for i in self.selected if self.files[i] != ".."] if self.selected else [self.files[self.cursor]]
        if ".." in items:
            items.remove("..")
        
        self.stdscr.addstr(0, 0, "Choose format (zip/tar): ", curses.color_pair(1))
        curses.echo()
        compress_format = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        
        if compress_format in ["zip", "tar"]:
            self.stdscr.addstr(0, 0, "Enter archive name: ", curses.color_pair(1))
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
        self.stdscr.addstr(0, 0, "Enter filter pattern (e.g., *.txt): ", curses.color_pair(1))
        curses.echo()
        filter_pattern = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        if filter_pattern:
            self.files = [".."] + [item for item in os.listdir(self.current_path) 
                          if os.path.isdir(os.path.join(self.current_path, item)) or 
                          any(item.endswith(ext) for ext in filter_pattern.split(','))]
            self.cursor = 0
            self.offset = 0

    def edit_text_file(self):
        item = self.files[self.cursor]
        if item == "..":
            return
        item_path = os.path.join(self.current_path, item)
        if os.path.isfile(item_path):
            curses.def_prog_mode()
            os.system(f'nano {item_path}')
            curses.reset_prog_mode()
            self.stdscr.refresh()

    def file_diff(self):
        self.stdscr.addstr(0, 0, "Enter path of first file: ", curses.color_pair(1))
        curses.echo()
        file1 = self.stdscr.getstr().decode('utf-8')
        self.stdscr.addstr(1, 0, "Enter path of second file: ", curses.color_pair(1))
        file2 = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        
        if file1 and file2:
            with open(file1, 'r') as f1, open(file2, 'r') as f2:
                diff = list(difflib.unified_diff(f1.readlines(), f2.readlines(), fromfile=file1, tofile=file2))
            
            self.stdscr.clear()
            for i, line in enumerate(diff):
                if line.startswith('+'):
                    self.stdscr.addstr(i, 0, line, curses.color_pair(2))
                elif line.startswith('-'):
                    self.stdscr.addstr(i, 0, line, curses.color_pair(3))
                else:
                    self.stdscr.addstr(i, 0, line, curses.color_pair(4))
            self.stdscr.getch()

    def change_sort(self):
        self.stdscr.addstr(0, 0, "Sort by (name/size/date/type): ", curses.color_pair(1))
        curses.echo()
        sort_key = self.stdscr.getstr().decode('utf-8')
        curses.noecho()
        if sort_key in ["name", "size", "date", "type"]:
            if sort_key == self.sort_key:
                self.reverse_sort = not self.reverse_sort
            else:
                self.sort_key = sort_key
                self.reverse_sort = False

    def show_help(self):
        help_text = """
        File Explorer Help:
        
        Navigation:
        - Arrow keys: Move cursor
        - Enter: Open file/directory
        - b: Go back to parent directory
        
        File Operations:
        - Space: Select/Deselect item
        - n: Create new item
        - d: Delete item
        - r: Rename item
        - c: Copy item
        - m: Move item
        - k: Bulk operations
        - p: Show/Change permissions
        - z: Compress items
        
        View and Edit:
        - f: Filter files
        - e: Edit text file
        - i: Compare files (diff)
        
        Other:
        - s: Change sort order
        - h: Show this help
        - q: Quit
        
        Press any key to close help...
        """
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, help_text, curses.color_pair(4))
        self.stdscr.getch()

def main(stdscr):
    explorer = FileExplorer(stdscr)
    explorer.run()

wrapper(main)
