import os
import sqlite3
import paramiko
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.simpledialog as simpledialog


# SQLite Database setup
conn = sqlite3.connect('connections.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        host TEXT NOT NULL,
        port INTEGER NOT NULL,
        username TEXT NOT NULL,
        password TEXT,
        key_file TEXT
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY,
        theme TEXT NOT NULL
    )
''')
conn.commit()

# SSH Connection Global Variable
ssh = None
current_path = '/'  # Initial directory path

# Load saved theme
cursor.execute("SELECT theme FROM settings WHERE id = 1")
row = cursor.fetchone()
current_theme = row[0] if row else 'light'

def set_theme(theme):
    global current_theme
    current_theme = theme
    style = ttk.Style()

    if theme == 'dark':
        style.theme_use('clam')
        style.configure('.', background='#333333', foreground='white')
        style.configure('Treeview', background='#444444', foreground='white', fieldbackground='#444444')
        style.map('Treeview', background=[('selected', '#555555')])
        root.config(bg='#333333')
    else:
        style.theme_use('default')
        style.configure('.', background='#d9d9d9', foreground='black')
        style.configure('Treeview', background='#d9d9d9', foreground='black', fieldbackground='#d9d9d9')
        style.map('Treeview', background=[('selected', '#333333')])
        root.config(bg='#d9d9d9')

    # Save theme preference
    cursor.execute('''
        INSERT OR REPLACE INTO settings (id, theme) VALUES (1, ?)
    ''', (theme,))
    conn.commit()

def center_window(window, width, height):
    """Centers a window on the screen or within the parent window."""
    if window.master:  # If the window has a parent
        parent = window.master
        # Get the parent window's dimensions
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        
        # Calculate center position relative to the parent window
        x = int(parent_x + (parent_width / 2) - (width / 2))
        y = int(parent_y + (parent_height / 2) - (height / 2))
    else:
        # Center on the screen if no parent window
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
    
    # Set the window size and position
    window.geometry(f'{width}x{height}+{x}+{y}')

def custom_simpledialog(prompt, title="Input", parent=None, is_password=False):
    """Displays a custom simple dialog centered on the parent window or screen.
    If is_password is True, masks the input with '*'."""
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    center_window(dialog, 300, 150)
    
    # Create a frame for the content
    frame = ttk.Frame(dialog, padding="10")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Create and place the prompt label
    ttk.Label(frame, text=prompt).pack(pady=5)
    
    # Create an entry widget for user input
    entry = ttk.Entry(frame, show='*' if is_password else '', width=40)
    entry.pack(pady=5)
    entry.focus_set()  # Set focus to the entry widget
    
    # Variable to store user input
    user_input = tk.StringVar()

    def on_ok():
        user_input.set(entry.get())
        dialog.destroy()

    def on_cancel():
        user_input.set('')
        dialog.destroy()

    # Bind Enter key to OK button
    def on_enter(event):
        on_ok()
        
    entry.bind('<Return>', on_enter)

    # Create OK and Cancel buttons
    buttons_frame = ttk.Frame(frame)
    buttons_frame.pack(pady=10)

    ttk.Button(buttons_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
    ttk.Button(buttons_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)

    # Wait for dialog to close
    dialog.wait_window(dialog)
    return user_input.get()

def connect_ssh(host, port, username, password, key_file=None, windows_to_close=[]):
    global ssh
    if ssh:
        ssh.close()
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        if key_file:
            key_file = key_file.strip()
            if os.path.isfile(key_file):
                try:
                    # Determine the key type from the file content
                    key_type = None
                    with open(key_file, 'r') as f:
                        key_data = f.read()
                        if 'OPENSSH PRIVATE KEY' in key_data:
                            key_type = 'OPENSSH'
                        elif 'RSA' in key_data:
                            key_type = 'RSA'
                        elif 'DSA' in key_data:
                            key_type = 'DSA'
                        elif 'ECDSA' in key_data:
                            key_type = 'ECDSA'
                        elif 'ED25519' in key_data:
                            key_type = 'ED25519'
                        else:
                            raise ValueError("Unsupported key format.")
                    
                    # Load the private key based on its type
                    if key_type == 'OPENSSH':
                        private_key = paramiko.Ed25519Key.from_private_key_file(key_file)
                    elif key_type == 'RSA':
                        private_key = paramiko.RSAKey.from_private_key_file(key_file)
                    elif key_type == 'DSA':
                        private_key = paramiko.DSSKey.from_private_key_file(key_file)
                    elif key_type == 'ECDSA':
                        private_key = paramiko.ECDSAKey.from_private_key_file(key_file)
                    elif key_type == 'ED25519':
                        private_key = paramiko.Ed25519Key.from_private_key_file(key_file)
                    else:
                        raise ValueError("Unsupported key type or key format.")
                    
                    ssh.connect(host, port=port, username=username, pkey=private_key)
                
                except paramiko.PasswordRequiredException:
                    # Prompt for passphrase if key is encrypted
                    passphrase = custom_simpledialog("Enter passphrase for the private key:", title="Passphrase", is_password=True)
                    if key_type == 'OPENSSH':
                        private_key = paramiko.Ed25519Key.from_private_key_file(key_file, password=passphrase)
                    elif key_type == 'RSA':
                        private_key = paramiko.RSAKey.from_private_key_file(key_file, password=passphrase)
                    elif key_type == 'DSA':
                        private_key = paramiko.DSSKey.from_private_key_file(key_file, password=passphrase)
                    elif key_type == 'ECDSA':
                        private_key = paramiko.ECDSAKey.from_private_key_file(key_file, password=passphrase)
                    elif key_type == 'ED25519':
                        private_key = paramiko.Ed25519Key.from_private_key_file(key_file, password=passphrase)
                    else:
                        raise ValueError("Unsupported key type or key format.")
                    
                    ssh.connect(host, port=port, username=username, pkey=private_key)
            
            else:
                raise FileNotFoundError(f"Private key file not found: {key_file}")
        
        else:
            # Connect using password if no key file is provided
            ssh.connect(host, port=port, username=username, password=password)

        messagebox.showinfo("Success", "Connected to the server!")

        # Close all passed windows
        for window in windows_to_close:
            window.destroy()

        fetch_directory(current_path)  # Fetch and display files from the current directory
    
    except paramiko.AuthenticationException:
        messagebox.showerror("Authentication Error", "Authentication failed, please verify your credentials.")
    except paramiko.SSHException as e:
        messagebox.showerror("SSH Error", f"SSH error occurred: {str(e)}")
    except FileNotFoundError as e:
        messagebox.showerror("File Error", str(e))
    except ValueError as e:
        messagebox.showerror("Key Error", str(e))
    except Exception as e:
        messagebox.showerror("Connection Error", str(e))

def add_connection(edit=False, conn_id=None):
    def save_connection():
        host = host_entry.get()
        port = port_entry.get()
        username = user_entry.get()
        password = pass_entry.get()
        key_file = key_entry.get()

        if not host or not port or not username:
            messagebox.showerror("Input Error", "Please fill in all required fields (Host, Port, Username).")
            return

        if edit and conn_id:
            # Update existing connection
            cursor.execute('''
                UPDATE connections
                SET host = ?, port = ?, username = ?, password = ?, key_file = ?
                WHERE id = ?
            ''', (host, port, username, password, key_file, conn_id))
        else:
            # Insert new connection
            cursor.execute('''
                INSERT INTO connections (host, port, username, password, key_file)
                VALUES (?, ?, ?, ?, ?)
            ''', (host, port, username, password, key_file))

        conn.commit()
        messagebox.showinfo("Success", "Connection saved successfully.")
        add_window.destroy()
        refresh_connections()  # Refresh list in manage connections

    add_window = tk.Toplevel(root)
    add_window.title("Edit Connection" if edit else "Add New Connection")
    center_window(add_window, 500, 300)

    # Host input
    ttk.Label(add_window, text="Host:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    host_entry = ttk.Entry(add_window, width=30)
    host_entry.grid(row=0, column=1, padx=5, pady=5)

    # Port input
    ttk.Label(add_window, text="Port:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    port_entry = ttk.Entry(add_window, width=30)
    port_entry.insert(0, "22")  # Default port
    port_entry.grid(row=1, column=1, padx=5, pady=5)

    # Username input
    ttk.Label(add_window, text="Username:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
    user_entry = ttk.Entry(add_window, width=30)
    user_entry.grid(row=2, column=1, padx=5, pady=5)

    # Password input
    ttk.Label(add_window, text="Password:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
    pass_entry = ttk.Entry(add_window, width=30, show="*")
    pass_entry.grid(row=3, column=1, padx=5, pady=5)

    # SSH Key input
    ttk.Label(add_window, text="SSH Key File:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
    key_entry = ttk.Entry(add_window, width=30)
    key_entry.grid(row=4, column=1, padx=5, pady=5)

    # Browse button for SSH key file
    def browse_key_file():
        key_path = filedialog.askopenfilename(filetypes=[("All Files", "*.*"), ("PEM Files", "*.pem")])
        if key_path:
            key_entry.delete(0, tk.END)
            key_entry.insert(0, key_path)

    browse_button = ttk.Button(add_window, text="Browse", command=browse_key_file)
    browse_button.grid(row=4, column=2, padx=5, pady=5)

    # Populate fields if editing
    if edit and conn_id:
        cursor.execute("SELECT host, port, username, password, key_file FROM connections WHERE id = ?", (conn_id,))
        row = cursor.fetchone()
        if row:
            host_entry.insert(0, row[0])
            port_entry.insert(0, row[1])
            user_entry.insert(0, row[2])
            pass_entry.insert(0, row[3])
            key_entry.insert(0, row[4])

    # Save button
    save_button = ttk.Button(add_window, text="Save Connection", command=save_connection)
    save_button.grid(row=5, column=1, padx=5, pady=10, sticky=tk.E)

def manage_connections():
    def edit_connection(conn_id):
        add_connection(edit=True, conn_id=conn_id)

    def delete_connection(conn_id):
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this connection?")
        if confirm:
            cursor.execute("DELETE FROM connections WHERE id = ?", (conn_id,))
            conn.commit()
            messagebox.showinfo("Success", "Connection deleted.")
            refresh_connections()

    def connect_to_selected():
        selected_item = tree.selection()
        if selected_item:
            conn_id = selected_item[0]  # Get the selected item ID
            cursor.execute("SELECT host, port, username, password, key_file FROM connections WHERE id = ?", (conn_id,))
            row = cursor.fetchone()
            if row:
                # Pass the current window to close it after a successful connection
                connect_ssh(*row, windows_to_close=[manage_window])
            else:
                messagebox.showerror("Connection Error", "Selected connection details are missing.")
        else:
            messagebox.showwarning("Selection Error", "Please select a connection to connect.")

    manage_window = tk.Toplevel(root)
    manage_window.title("Manage Connections")
    center_window(manage_window, 800, 400)
    manage_window.minsize(width=800, height=400)  # Set minimum size for the window

    # Connection List
    tree = ttk.Treeview(manage_window, columns=('Host', 'Port', 'Username'), show='headings')
    tree.heading('Host', text="Host")
    tree.heading('Port', text="Port")
    tree.heading('Username', text="Username")
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def refresh_connections():
        tree.delete(*tree.get_children())
        cursor.execute("SELECT id, host, port, username FROM connections")
        for row in cursor.fetchall():
            tree.insert('', 'end', values=row[1:], iid=row[0])

    refresh_connections()

    # Add, Edit, Delete, and Connect buttons
    def on_add():
        add_connection()

    def on_edit():
        selected_item = tree.selection()
        if selected_item:
            conn_id = selected_item[0]  # Get the selected item ID
            edit_connection(conn_id)

    def on_delete():
        selected_item = tree.selection()
        if selected_item:
            conn_id = selected_item[0]  # Get the selected item ID
            delete_connection(conn_id)

    def on_connect():
        connect_to_selected()

    add_button = ttk.Button(manage_window, text="Add Connection", command=on_add)
    add_button.pack(padx=10, pady=5, side=tk.TOP, fill=tk.X)

    edit_button = ttk.Button(manage_window, text="Edit Connection", command=on_edit)
    edit_button.pack(padx=10, pady=5, side=tk.TOP, fill=tk.X)

    delete_button = ttk.Button(manage_window, text="Delete Connection", command=on_delete)
    delete_button.pack(padx=10, pady=5, side=tk.TOP, fill=tk.X)

    connect_button = ttk.Button(manage_window, text="Connect", command=on_connect)
    connect_button.pack(padx=10, pady=10, side=tk.BOTTOM, fill=tk.X)


def fetch_directory(path):
    global ssh, current_path
    current_path = path  # Update current path
    if ssh:
        try:
            # Execute command to list files
            stdin, stdout, stderr = ssh.exec_command(f'ls -l {path}')
            
            # Read and decode the output
            files = stdout.read().decode().strip().split('\n')
            errors = stderr.read().decode().strip()
            if errors:
                messagebox.showerror("Fetch Error", errors)

            # Add the "../" entry manually at the start
            files.insert(0, '../')
            
            update_file_list(files)
        except Exception as e:
            messagebox.showerror("Fetch Error", str(e))

def update_file_list(files):
    file_listbox.delete(*file_listbox.get_children())
    
    if not files:
        return
    
    for file in files:
        parts = file.split(maxsplit=8)
        if len(parts) >= 9:
            name = parts[-1]
            size = parts[4]
            permissions = parts[0]
            try:
                # Convert permissions to octal
                octal_permissions = get_octal_permissions(name)
            except ValueError:
                octal_permissions = 'N/A'
            file_listbox.insert('', 'end', values=(name, size, permissions, octal_permissions))
        else:
            file_listbox.insert('', 'end', values=(file, '', '', ''))

def get_octal_permissions(filename):
    try:
        # Execute the stat command to get file permissions in octal format
        stdin, stdout, stderr = ssh.exec_command(f'stat -c %a {os.path.join(current_path, filename)}')
        permissions = stdout.read().decode().strip()
        
        if permissions:
            return permissions
        else:
            return 'N/A'
    except Exception as e:
        return 'N/A'

def on_double_click(event):
    item = file_listbox.selection()
    if item:
        filename = file_listbox.item(item, 'values')[0]
        
        # Check if the selected item is "../"
        if filename == "../":
            navigate_up()
        else:
            # Normal behavior: open the selected directory or do other actions
            path = os.path.join(current_path, filename)
            fetch_directory(path)

def change_permissions():
    selected_item = file_listbox.selection()
    if selected_item:
        filename = file_listbox.item(selected_item, 'values')[0]
        path = os.path.join(current_path, filename)
        new_permissions = custom_simpledialog(
            prompt=f"Enter new permissions for {filename} (e.g., 755):",
            title="Permissions",
            is_password=False
        )
        if new_permissions:
            try:
                ssh.exec_command(f'chmod {new_permissions} {path}')
                fetch_directory(current_path)  # Refresh file list
                messagebox.showinfo("Success", f"Permissions changed for {filename}.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
    else:
        messagebox.showwarning("Selection Error", "Please select a file or directory to change permissions.")

def navigate_up():
    global current_path
    # Go up one directory level
    parent_path = os.path.dirname(current_path.rstrip('/'))
    if parent_path:
        fetch_directory(parent_path)
    else:
        messagebox.showwarning("Navigation Error", "Already at the root directory or invalid path.")

def show_about():
    about_window = tk.Toplevel(root)
    about_window.title("About")
    center_window(about_window, 300, 200)
    main_text = tk.Label(about_window, text="Permissions Manager\nVersion 1.0", font=("Helvetica", 12))
    main_text.pack(pady=10)
    smaller_text = tk.Label(about_window, text="This is a user-friendly, free tool designed\nto streamline and manage file permissions\neffortlessly. It empowers users to easily\nconfigure, modify, and monitor access\nlevels to files, ensuring optimal\nsecurity and organization within\nyour system.", font=("Helvetica", 10))
    smaller_text.pack(pady=5)

def show_help():
    help_window = tk.Toplevel(root)
    help_window.title("Help")
    center_window(help_window, 300, 200)
    main_text = tk.Label(help_window, text="Help", font=("Helvetica", 12))
    main_text.pack(pady=10)

    def open_fake_url(event):
        webbrowser.open("https://github.com/ncklinux/PermissionsManager")

    link = tk.Label(help_window, text="GitHub issues", font=("Helvetica", 10), fg="blue", cursor="hand2")
    link.pack(pady=5)
    link.bind("<Button-1>", open_fake_url)
    smaller_text = tk.Label(help_window, text="Currently there is no help page or wiki\nopen an issue on GiHub", font=("Helvetica", 10))
    smaller_text.pack(pady=5)

def show_settings():
    settings_window = tk.Toplevel(root)
    settings_window.title("Settings")
    center_window(settings_window, 300, 200)

    # Light/Dark Mode toggle
    def switch_theme():
        if current_theme == 'light':
            set_theme('dark')
        else:
            set_theme('light')

    theme_button = ttk.Button(settings_window, text="Switch Theme", command=switch_theme)
    theme_button.pack(pady=10)

# Main Window
root = tk.Tk()
root.title("Permissions Manager")
root.geometry('1200x900')

frame = ttk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Create a container frame to add padding
listbox_frame = ttk.Frame(frame)
listbox_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

# Create the Treeview inside the container frame
file_listbox = ttk.Treeview(listbox_frame, columns=('Name', 'Size', 'Permissions', 'Octal Permissions'), show='headings')
file_listbox.heading('Name', text="Name")
file_listbox.heading('Size', text="Size")
file_listbox.heading('Permissions', text="Permissions")
file_listbox.heading('Octal Permissions', text="Octal Permissions")
file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
file_listbox.bind('<Double-1>', on_double_click)  # Bind double-click event to navigation

change_permissions_button = ttk.Button(frame, text="Change Permissions", command=change_permissions)
change_permissions_button.pack(side=tk.TOP, pady=(0, 5), anchor='w')

# navigate_up_button = ttk.Button(frame, text="Up", command=navigate_up)
# navigate_up_button.pack(side=tk.BOTTOM, pady=5)

menubar = tk.Menu(root)
root.config(menu=menubar)

file_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="File", menu=file_menu)
file_menu.add_command(label="Manage Connections", command=manage_connections)
file_menu.add_separator()
file_menu.add_command(label="Exit", command=root.quit)

settings_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Settings", menu=settings_menu)
settings_menu.add_command(label="Settings", command=show_settings)

help_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="Help", menu=help_menu)
help_menu.add_command(label="Help", command=show_help)
help_menu.add_command(label="About", command=show_about)

# Example of initial theme setup
set_theme(current_theme)

root.mainloop()

# Close database connection on exit
conn.close()
