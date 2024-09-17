import tkinter as tk
from tkinter import filedialog

import pygments

from pygments import highlight,styles
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name

import os

from pygments.formatters.terminal import TerminalFormatter

#some constants for style
style = styles.get_style_by_name('monokai')
fotmatter=TerminalFormatter(style=style,full=True,linenos=True)


def clear_highlight(text_widget):
    text_widget.tag_remove("Token.Comment", "1.0", tk.END)
    text_widget.tag_remove("Token.Keyword", "1.0", tk.END)
    text_widget.tag_remove("Token.Literal.String", "1.0", tk.END)
    text_widget.tag_remove("Token.Operator", "1.0", tk.END)
    text_widget.tag_remove("Token.Name.Function", "1.0", tk.END)


def apply_highlight(text_widget, Raw_text):
    tokens = pygments.lex(Raw_text, PythonLexer())

    current_index = "1.0"

    for token_type, token_value in tokens:
        end_index = text_widget.index(f"{current_index}+{len(token_value)}c")

        # Tokens for keywords
        if str(token_type).startswith("Token.Keyword"):
            text_widget.tag_add("Token.Keyword", current_index, end_index)
        elif str(token_type).startswith("Token.Comment"):
            text_widget.tag_add("Token.Comment", current_index, end_index)
        elif str(token_type).startswith("Token.Literal.String"):
            text_widget.tag_add("Token.Literal.String", current_index, end_index)
        elif str(token_type).startswith("Token.Operator"):
            text_widget.tag_add("Token.Operator", current_index, end_index)
        elif str(token_type).startswith("Token.Name.Function"):
            text_widget.tag_add("Token.Name.Function", current_index, end_index)
        elif str(token_type).startswith("Token.Name.Class"):
            text_widget.tag_add("Token.Name.Class", current_index, end_index)
        elif str(token_type).startswith("Token.Name.Builtin"):
            text_widget.tag_add("Token.Name.Builtin", current_index,end_index)
        elif str(token_type).startswith("Token.Name.Variable"):
            text_widget.tag_add("Token.Name.Variable", current_index, end_index)
        elif str(token_type).startswith("Token.Name.Function"):
            text_widget.tag_add("Token.Name.Function", current_index, end_index)


        current_index = end_index


def highlighted_text(event):
    text_widget = event.widget
    Raw_text = text_widget.get("1.0", "end-1c")


    clear_highlight(text_widget)


    apply_highlight(text_widget, Raw_text)



def Save_function():
    file_path=filedialog.asksaveasfilename()
    Text_of_file=text_widget.get("1.0","end-1c")
    f = open(file_path,'w')
    f.write(Text_of_file)
    print(Text_of_file)
    f.close()

def Load_function():
    file_path = filedialog.askopenfilename()
    if os.path.exists(file_path):
        f = open(file_path, 'r')
        Text_of_file = f.read()
        text_widget.delete("1.0", tk.END)
        text_widget.insert(tk.INSERT, Text_of_file)
        print(Text_of_file)
        f.close()
    else:
        print("File does not exist")

root = tk.Tk()

Btn_frame = tk.Frame(root)
Text_frame = tk.Frame(root)

Text_frame.grid(row=1, column=0, sticky="nsew")

text_widget = tk.Text(Text_frame,wrap='word')
text_widget.grid(row=0, column=0, sticky="nsew")

Quit_btn_widget = tk.Button(Btn_frame, text="Quit",command=root.destroy, padx=5, pady=5)
Quit_btn_widget.grid(row=0,column=3)

Save_btn_widget = tk.Button(Btn_frame, text="Save",command=Save_function, padx=5, pady=5)
Save_btn_widget.grid(row=0,column=2)

Load_btn_widget = tk.Button(Btn_frame, text="Load",command=Load_function, padx=5, pady=5)
Load_btn_widget.grid(row=0,column=1)

Set_btn_widget = tk.Button(Btn_frame, text="Setting", padx=5, pady=5)
Set_btn_widget.grid(row=0,column=0)

Btn_frame.grid(row=0, column=0, sticky="ew")

root.rowconfigure(1, weight=1)
root.columnconfigure(0, weight=1)

Text_frame.rowconfigure(0, weight=1)
Text_frame.columnconfigure(0, weight=1)

root.minsize(width=300, height=200)

text_widget.bind('<KeyRelease>',highlighted_text)

text_widget.tag_configure("Token.Keyword", foreground="blue")
text_widget.tag_configure("Token.Comment", foreground="green")
text_widget.tag_configure("Token.Literal.String", foreground="orange")
text_widget.tag_configure("Token.Operator", foreground="purple")
text_widget.tag_configure("Token.Name.Function", foreground="brown")
text_widget.tag_configure("Token.Name.Class", foreground="red", font=('TkDefaultFont', 10, 'bold'))
text_widget.tag_configure("Token.Name.Builtin", foreground="magenta")
text_widget.tag_configure("Token.Name.Variable", foreground="darkcyan")
text_widget.tag_configure("Token.Name.Function", foreground="brown", font=('TkDefaultFont', 10, 'italic'))




root.mainloop()

