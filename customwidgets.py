"""Module `customwidgets.py` is used to define various kivy GUI elements
and subclasses used by the Gravity app in `main.py`.
They are independent of the rest of the app and can also be used elsewhere.

See `__all__` and the individual class documentaions for more info."""

from __future__ import annotations

from kivy.uix.settings import *
from kivy.uix.settings import InterfaceWithSidebar
from kivy.uix.settings import SettingSpacer
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.stencilview import StencilView
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image, AsyncImage
from kivy.properties import *
from kivy.core.window import Window
from kivy.graphics import *
from kivy.app import App
from kivy.metrics import dp
from kivy.lang import Builder
from kivy.logger import Logger

import os, sys, re
from typing import TextIO, Union, Iterable, Callable, Any

__all__ = ['InfoDialog', 'ColourChooser', 'ColourChooserPopup',
           'GravSettings', 'QuestionDialog', 'SettingSpacer',
           'SaveFileDialog', 'OpenFileDialog', 'WrapLabel', 'BGLabel',
           'StencilBox', 'NumEntry', 'ContentDialog']


class WrapLabel(Label):
    """A Label that prevents the text overflowing beyond its boundary.
    The text size binding is performed in `kv` language, and no other
    methods are defined here - it behaves as a regular `kivy.uix.label.Label`
    otherwise."""
    pass
Builder.load_string("""
<WrapLabel>:
    text_size: self.width, None
""", filename='cw_WrapLabel.kv')

class BGLabel(Label):
    r"""A label with a custom RGBA background colour.
    
    :bgcolour: A list of 4 floats, each from 0.0 to 1.0, representing an RGBA colour.
    :\**kwargs: Any other keyword args, passed to the `kivy.uix.label.Label` constructor.

    A coloured rectangle is drawn covering the Label's size (*not its `text_size`*,
    also use WrapLabel to constrain the text to this size !) in the `canvas.before`
    statement using the `kv` language.
    No other methods are defined here.
    """
    bgcolour = ListProperty([0,0,0,0])

    def __init__(self, **kwargs):
        self.bgcolour = kwargs.pop('bgcolour', [0,0,0,0])
        super(BGLabel, self).__init__(**kwargs)

Builder.load_string("""
<BGLabel>:
    canvas.before:
        Color:
            rgba: root.bgcolour
        Rectangle:
            size: self.size
            pos: self.pos
""", filename='cw_BGLabel.kv')

class NumEntry(TextInput):
    """A single line text entry field that only accepts numeric input, with
    additional features for validation.
    
    :autovalidate: bool, Whether to automatically check if the input can
        be parsed as a valid python `float`
    :valid: bool, Property that indicates whether the current value is numerically
        valid. Supports both *get* and *set*.
    :ontext_callbacks: A list of functions that will be called each time the text
        in the input changes. They are called with 2 positional arguments - the 
        instance of this widget, and its current text value. If an unhandled exception 
        occurs in the call, it will be caught and passed to `kivy.logger.Logger`.
    :\**kwargs: Any other keyword args will be passed to the constructor of
        `kivy.uix.textinput.TextInput`.
        
    Call `.get()` to get the numeric value as a float, or `None` if it is invalid.
    
    The text colour is black by default and red while it contains and invalid value.
    The background is set to grey when the `readonly` property is True, and white otherwise.
    """

    autovalidate = BooleanProperty(True)
    valid = BooleanProperty(False)
    ontext_callbacks = ListProperty([])

    def __init__(self, **kwargs):
        super(NumEntry, self).__init__(**kwargs)
        self.multiline = False
        self.write_tab = False

    def insert_text(self, substring:str, from_undo:bool=False) -> str:
        """Allow only unicode digit characters, ``+``, ``-``, ``e`` or ``E`` and ``.``
        to be typed into the textbox. Insert nothing if there are chars besides these."""
        if re.search("[^\d\.\+\-eE]", substring):
            return super(NumEntry, self).insert_text('', from_undo=from_undo)
        return super(NumEntry, self).insert_text(substring, from_undo=from_undo)

    def on_text(self, widget:NumEntry, text:str):
        """Called automatically by kivy whenever `self.text` changes. 
        If required, autovalidate the text; and then call all functions in
        `self.ontext_callbacks`."""
        if self.autovalidate:
            try:
                float(text)
                self.valid = True
            except ValueError:
                self.valid = False
        for fn in self.ontext_callbacks:
            try:
                fn(widget, text)
            except Exception as e:
                Logger.error(f'Callback : Error while calling {fn} from on_text of {self}', 
                exc_info=str(e))

    def on_valid(self, widget, val):
        """Called automatically by kivy whenever `self.valid` is set.
        Change the text colour between red (invalid) and black (normal)."""
        if val:
            self.foreground_color = [0,0,0,1]
        else:
            self.foreground_color = [1,0,0,1]

    def get(self) -> Union[float, None]:
        """Return the currently held value as a `float` if it can be parsed correctly,
        else return `None` if it cannot."""
        try:
            return float(self.text)
        except ValueError:
            return None

    def on_readonly(self, widget, val):
        """Called automatically by kivy whenever `self.readonly` is set.
        Change the background colour between grey (disabled) and white (normal)."""
        if val:
            self.background_color = [0.7,0.71,0.7,1]
        else:
            self.background_color = [1,1,1,1]


# ------------------- Info Dialog & Question Dialog ----------------------------

class InfoDialog(Popup):
    r"""Create a kivy Popup to display a textual message with a title, 
    with an 'OK' button.

    Optional keyword arguments - 
    
    :title: str, Title of the popup, defaults to `'Info'`.
    :message: str, Detailed message text that will be displayed below the title,
        defaults to `''`
    :action: A callable that will be called (without any arguments) when the user
        clicks on **OK**. On clicking this, the dialog will also close. No
        exception handling is performed during the call.
    :size_hint: tuple of 2 floats, Kivy `size_hint` for the popup dialog, uses
        (0.5, 0.5) as the default if unspecified instead of filling the window.
    :show: bool, Whether to open/display the popup immediately after creation,
        defaults to `True`
    :\**kwargs: Any other keyword args will be passed to the constructor of
        `kivy.uix.popup.Popup`.
    """

    def __init__(self, title:str='Info', message:str="", 
            action: Callable[[],Any] = None, 
            size_hint: tuple[float,float] = (0.5,0.5),
            show:bool = True, **kwargs):
        self.title = title
        self.message = message
        kwargs.pop('content', None)

        content = BoxLayout(orientation='vertical')
        content.add_widget(WrapLabel(text=self.message,
                                     size_hint=(0.9, 0.9)))
        if action is None or action is self.dismiss:
            action = self.dismiss
        else :
            action = self._closeandrun(action)
        content.add_widget(Button(text='OK', on_release=action,
                                  size_hint=(1, None), height='75dp',
                                  pos_hint={'center_x':0.5}))
        super(InfoDialog, self).__init__(title=self.title, content=content,
                                         size_hint=size_hint, **kwargs)
        if show :
            self.open()

    def _closeandrun(self, fn):
        # Close the popup and then call the user action
        def finish(*args, **kwargs):
            self.dismiss()
            fn()
        return finish


class QuestionDialog(Popup):
    r"""Create a kivy Popup to prompt the user with a question, with 
    'Yes' and 'No' buttons.

    Optional keyword arguments - 
    
    :title: str, Title of the popup, defaults to `'Confirm'`.
    :question: str, Detailed question text that will be displayed below the title,
        defaults to `''`
    :action: A callable that will be called with the positional argument `True`
        when the user clicks on **Yes**, and with `False` when the user clicks on 
        **No**. On clicking these, the dialog will also close. No exception handling
        is performed during the call.
    :size_hint: tuple of 2 floats, Kivy `size_hint` for the popup dialog, uses
        (0.5, 0.5) as the default if unspecified instead of filling the window.
    :show: bool, Whether to open/display the popup immediately after creation,
        defaults to `True`
    :\**kwargs: Any other keyword args will be passed to the constructor of
        `kivy.uix.popup.Popup`.
    """

    def __init__(self, title:str="Confirm", question:str="", 
            action: Callable[[bool],Any] = None, 
            size_hint: tuple[float,float] = (0.5,0.5),
            show:bool = True, **kwargs):
        self.title = title
        self.question = question
        kwargs.pop('content', None)

        content = BoxLayout(orientation='vertical')
        content.add_widget(WrapLabel(text=self.question, size_hint=(0.9, 0.9)))
        if action is None or action is self.dismiss:
            action = self.dismiss
        else :
            action = self._closeandrun(action)
        btns = BoxLayout(spacing='5dp', padding='10dp',
                         size_hint=(0.9, None), height='75dp',
                         pos_hint={'center_x':0.5})
        btns.add_widget(Button(text='Yes', on_release=lambda arg: action(True)))
        btns.add_widget(Button(text='No', on_release=lambda arg: action(False)))
        content.add_widget(btns)
        super(QuestionDialog, self).__init__(title=self.title, content=content,
                                         size_hint=size_hint, **kwargs)
        if show: 
            self.open()

    def _closeandrun(self, fn):
        # Close the popup and then call the user action
        def finish(*args, **kwargs):
            self.dismiss()
            fn(*args, **kwargs)
        return finish


class ContentDialog(Popup):
    r"""Create a kivy Popup to display a vertically scrollable sequence of 
    non-interactive / static widgets such as Labels (text) and Images. Also includes
    an 'OK' button like the `InfoDialog`.

    Another purpose of using this dialog to display the content is to also handle 
    resizing the text/images appropriately so that they are displayed 'normally',
    avoiding the kivy behaviour of shrinking/expanding all the widgets inside a 
    layout such as `BoxLayout` to exactly fit its width & height. This is done
    by appropriately setting the width & height of all label/image elements 
    everytime the popup is opened.
    Refer to the source of `self._updatesize()` for more details.

    Parameters - 

    :widgets: is the constructor parameter that specifies the widgets to be added. 
        It is a parsed-JSON style list of dicts. Each dict *must* contain the 
        key-value pair ``"class": widget type ``, where ``widget type`` is one of the 
        names in `ContentDialog.classes` (strings such as `Label` or `Image`, 
        `Seperator`, or generic `Widget`). Besides this, other optional key-value pairs
        are treated as kwargs to be passed to the constructor of the widget. Refer to
        the kivy docs for which arguments are accepted by each.

    Example (note that `WrapLabel` is defined in this module, not vanilla kivy)-
    >>> {'class':"WrapLabel", 'text':"abc", 'color':[0,0.5,1,1]}

    is equivalent to creating with kivy
    >>> WrapLabel(text=abc, color=[0,0.5,1,1])

    Optional keyword arguments - 
    
    :title: str, Title of the popup, defaults to `'Info'`.
    :size_hint: tuple of 2 floats, Kivy `size_hint` for the popup dialog, uses
        (0.5, 0.5) as the default if unspecified instead of filling the window.
    :padding: int or other format (see `kivy.uix.boxlayout.BoxLayout` docs), 
        Padding of the widgets in the list, defaults to `0`
    :spacing: int or other format (see `kivy.uix.boxlayout.BoxLayout` docs), 
        Spacing between the widgets in the list, defaults to `0`
    :action: A callable that will be called, without any arguments, when the user 
        clicks on the **OK** button. On clicking it, the dialog will also close. 
        No exception handling is performed during the call.
    :show: bool, Whether to open/display the popup immediately after creation,
        defaults to `True`
    :\**kwargs: Any other keyword args will be passed to the constructor of
        the scrollable area `kivy.uix.scrollview.ScrollView`.
    """

    classes = {'Label':Label, 'Image':Image, 'Widget':Widget,
        'Separator':SettingSpacer, 'WrapLabel':WrapLabel,
        'BGLabel':BGLabel, 'AsyncImage':AsyncImage}

    def __init__(self, widgets: Iterable[dict[str,Any]], title:str='Info',
            size_hint: tuple[float,float] = (0.5,0.5),
            padding:Any=0, spacing:Any=0,
            action: Callable[[],Any] = None, 
            show:bool = True, **kwargs):
        self.title = title
        if action is None or action is self.dismiss:
            action = self.dismiss
        else :
            action = self._closeandrun(action)

        content = BoxLayout(orientation='vertical', spacing='10dp')
        self.scrollarea = ScrollView(**kwargs)
        content.add_widget(self.scrollarea)
        footer = GridLayout(rows=1, size_hint=(1,None), height='50dp')
        footer.add_widget(Widget(size_hint=(0.333,1)))
        footer.add_widget(Button(text='OK', on_release=action,
                                  size_hint=(0.333, 0.8),
                                  pos_hint={'center_x':0.5}))
        footer.add_widget(Widget(size_hint=(0.333,1)))
        content.add_widget(footer)
        super(ContentDialog, self).__init__(title=self.title, content=content,
                                         size_hint=size_hint)
        
        self.widgetarea = BoxLayout(orientation='vertical',
            padding=padding, spacing=spacing, size_hint=(1,None),)
        self.scrollarea.add_widget(self.widgetarea)
        for w in widgets:
            try:
                c = w.pop('class', None)
                if c not in self.classes:
                    Logger.warning(f"ContentDialog : Widget {c} is not supported")
                    continue
                wgt = self.classes[c](**w)
                wgt.size_hint = (1, None)
                self.widgetarea.add_widget(wgt)
            except Exception as err:
                Logger.error(f"ContentDialog : Error creating widget {w}", 
                    exc_info = str(err))
                continue

        if show:
            self.open()

    def _closeandrun(self, fn):
        # ignore arguments passed & close the dialog, then call the function
        def finish(*args, **kwargs):
            self.dismiss()
            fn()
        return finish

    def open(self):
        """Open the popup, and resize all the text/image widgets neatly."""
        super(ContentDialog, self).open()
        self._updatesize()

    def _updatesize(self):
        """Manually compute the required sizes of all the Label and Image widgets
        to fit neatly in the layout. Start with a height of 10px for the entire 
        layout, find from kivy the actual size needed to contain the text/image
        texture *if* its width  equals the popup's width, and set its height
        and increase layout's height accordingly.
        
        Note: if the label isn't forced to wrap its text, it can still overflow
        horizontally though height/line spacing are adjusted."""
        self.widgetarea.height = 10
        for x in self.widgetarea.children:
            if any([isinstance(x, c) for c in \
                # Only these widgets have `texture_size` and `texture_update`
                (Label, Image, WrapLabel, AsyncImage, BGLabel)]):
                x.width = 0.95 * self.width
                # Use popup width, layout width may also be unpredictable
                x.texture_update()
                # Force the widget to resize its text/image content
                # (different from its own widget size)
                x.height = x.texture_size[1]
            self.widgetarea.height += x.height + self.widgetarea.spacing


# -------------------------- File I/O Dialogs ---------------------------------------

class SaveFileDialog(Popup):
    """Dialog containing a List-view file system browser, to use as a 'Save As'
    prompt. The user can select any folder location to save in, and enter a filename
    with extension. The dialog can return either an opened file object or strings 
    containing the path. It always checks that the file address chosen is valid,
    and also prompts the user if that path already exists, asking whether to replace
    it or choose another name.
    
    Optional keyword arguments - 
    
    :title: str, Title of the popup dialog, defaults to "Save As". This will be
        displayed at the top of the prompt.
    :size_hint: Tuple of 2 floats to use as the kivy size hint for the popup dialog.
        Defaults to (0.8, 0.8).
    :initial_dir: str (path), Address of a directory which the filechooser should
        initially open to. Use the program's directory (`"."`) if invalid or unspecified.
    :rootdir: str (path), Address of the topmost directory that will be accessible
        through the file browser, in the same filesystem tree. Use no particular
        location (`""`) if invalid or unspecified.
    :ext: str, Default file name extension (with preceding dot `.`) to append to 
        the filename, *if* the user has not entered one. Defaults to `""` if unspecified.
    
    :fileobj: bool, Whether to return a newly opened write-supporting file object at the
        chosen location (if True), or the chosen path and filename as strings (if False).
        Defaults to False.
    :action: callable, A function that will be called, when the user clicks 'Save' & 
        hence the dialog closes successfully. It will be called with 1 or 2 positional
        arguments depending on `fileobj` - 
        + 1 argument, the opened write-supporting TextIO if fileobj is True
        + 2 arguments, strings, the save location (directory) and the entered 
          filename with extension
        No error handling is performed during the function call. The action can also
        be `None` (default), then no callback will be performed.

    WARNING - If a newly opened file object is returned, you must `.close()` it after
              finishing. It cannot be closed automatically
              
    :mode: str, One of the default i/o modes to be used with Python's builtin `open()`
        for creating a file object. This overrules the default text-write mode if
        specified. No error handling is performed for an invalid mode to create a file.
    :encoding: str, The encoding format to use with `open()` for a text file object,
        defaults to `'utf-8'`. If `mode` is a binary mode, this must be `None`.
        No error handling is performed for an invalid encoding format.
    
    :show: bool, Whether to open the dialog automatically after creation.
        Defaults to True.
    :\**kwargs: Any other keyword args will be passed to the constructor of 
    `kivy.uix.popup.Popup`.

    The `kivy.uix.filechooser.FileChooserListView` widget is referenced by 
    `self.filechooser`, in case it needs to be customised further."""

    def __init__(self, title:str='Save As', size_hint:tuple[float,float]=(0.8,0.8),
            initial_dir:str=".", rootdir:str='', ext:str='', fileobj:bool=False, 
            action:Union[Callable[[TextIO],Any], Callable[[str,str],Any]] = None,
            mode:str='w', encoding:Union[str,None]='utf-8', show:bool=True, **kwargs):
        # Store various properties
        self.title = title
        self.idir = initial_dir
        self.root = rootdir
        self.ext = ext
        self.fileobj = fileobj
        self.mode = mode
        self.enc = encoding
        self.filename = ''
        # Ensure that given paths exist
        if not os.path.isdir(os.path.abspath(self.idir)) :
            self.idir = os.path.abspath('.')
        if not os.path.isdir(os.path.abspath(self.root)) :
            self.root = ''
        # Decorate callback 
        if action is None or action is self.dismiss:
            self.action = self.dismiss
        else :
            self.action = self._closeandrun(action)

        # Create GUI
        kwargs.pop('content', None)
        self.content = BoxLayout(orientation='vertical')
        self.filechooser = FileChooserListView(path=self.idir, rootpath=self.root)
        self.content.add_widget(self.filechooser)
        self.folderlbl = Label(text="  Location : "+self.idir, size_hint_y=None, 
            height='35dp')
        self.content.add_widget(self.folderlbl)
        self.filechooser.bind(path=self._updateflbl)
        self.filechooser.bind(selection=self._updatesel)
        self.namefield = TextInput(multiline=False, hint_text="Enter a filename", 
            text = "Untitled" + self.ext, size_hint_y=None, height='35dp', 
            on_text_validate = self.testvalid)
        self.content.add_widget(self.namefield)
        self.btns = BoxLayout(spacing='5dp', padding='10dp', size_hint=(0.9, None),
            height='75dp', pos_hint={'center_x':0.5})
        self.btns.add_widget(Button(text='Save', on_release=self.testvalid))
        self.btns.add_widget(Button(text='Cancel', on_release=self.dismiss))
        self.content.add_widget(self.btns)
        super(SaveFileDialog, self).__init__(title=self.title,
                                             content=self.content,
                                             size_hint=size_hint, **kwargs)
        if show:
            self.open()

    def _closeandrun(self, fn):
        # Close the dialog before performing the requested callabck
        def finish(*args, **kwargs):
            self.dismiss()
            if hasattr(fn, '__call__'):
                fn(*args, **kwargs)
        return finish

    def _updateflbl(self, widget, val):
        self.folderlbl.text = "  Location : "+os.path.abspath(val)

    def _updatesel(self, widget, val):
        if len(widget.selection) == 1:
            self.namefield.text = os.path.split(widget.selection[0])[1]

    def testvalid(self, widget, evalue=None):
        """Initiate the save process by ensuring that a file can be created at the
        given path. Prompt the user in case of a filename collision. If successful,
        proceed to perform `self.action`."""
        cwd = os.getcwd()
        try :
            os.chdir(self.filechooser.path)
            if len(self.namefield.text) == 0:
                InfoDialog(title='Error', message='Filename cannot be blank', show=True)
                os.chdir(cwd)
                return
            # Check for an extension, append default one if not present
            e = os.path.splitext(self.namefield.text)[1]
            if not e :
                self.filename =  self.namefield.text + self.ext
                self.namefield.text = self.filename
            else :
                self.filename = self.namefield.text
            # Check if filename is valid by trying to create the file exclusively
            # If a file object needs to be returned instead of the path, return this
            # Otherwise close & delete it, then return the path
            tmp = open(self.filename, 'x', encoding=self.enc)
            if self.fileobj and self.mode in ('w', 'x'):
                self.callfn(True, tmp)
                return
            tmp.close()
            os.remove(self.filename)
        
        except FileExistsError:
            QuestionDialog(question=f'"{self.filename}" already exists. Replace it ?',
                action=self.callfn)
            return
        except :
            # Invalid name or path
            Logger.error('SaveFileDialog : {}'.format(sys.exc_info()[2]))
            InfoDialog(title='Error', message='The specified address {} is invalid'.format(
                os.path.join(self.filechooser.path, self.namefield.text)))
            os.chdir(cwd)
            return
        finally :
            os.chdir(cwd)
        self.callfn(True)

    def callfn(self, yn, obj=None):
        """Call `self.action` with the appropriate arguments, if `yn` is True."""
        if yn :
            if self.fileobj:
                if obj is not None:
                    self.action(obj)
                else :
                    self.action(open(self.filename,self.mode,encoding=self.enc))
            else :
                self.action(self.filechooser.path, self.namefield.text)



class OpenFileDialog(Popup):
    """Dialog containing a List-view file system browser, to use as a file selection
    prompt. The user can select any file to open, and dialog can return either
    the opened file object or strings containing its path.
    
    Optional keyword arguments - 
    
    :title: str, Title of the popup dialog, defaults to "Open". This will be
        displayed at the top of the prompt.
    :size_hint: Tuple of 2 floats to use as the kivy size hint for the popup dialog.
        Defaults to (0.8, 0.8).
    :initial_dir: str (path), Address of a directory which the filechooser should
        initially open to. Use the program's directory (`"."`) if invalid or unspecified.
    :rootdir: str (path), Address of the topmost directory that will be accessible
        through the file browser, in the same filesystem tree. Use no particular
        location (`""`) if invalid or unspecified.
    
    :multiselect: bool, Whether the user can select multiple files for opening
        simultaneously. Defaults to False.
    :fileobj: bool, Whether to return the opened read-supporting file object (if True),
        or the chosen path and filename as strings (if False). Defaults to False.
    :action: callable, A function that will be called, when the user clicks 'Open' & 
        hence the dialog finishes successfully. It will be called with 1 or 2 positional
        arguments depending on `fileobj` and `multiselect`- 
        + 1 argument if fileobj is True, the opened read-supporting TextIO (if 
          multiselect is False) or a list of >=1 such objects (if multiselect is True)
        + 2 arguments, strings, if fileobj is False - the file's location (directory),
          and, its filename with extension (for 1 object only). If multiselect is True,
          the filename is a string containing several such names enclosed in double 
          quotes and seperated by spaces (E.g. `r'"a.txt" "b.png" "c"'`)
        No error handling is performed during the function call. The action can also
        be `None` (default), then no callback will be performed.

    WARNING - If a newly opened file object is returned, you must `.close()` it after
              finishing. It cannot be closed automatically
              
    :mode: str, One of the default i/o modes to be used with Python's builtin `open()`
        for creating a file object. This overrules the default text-read mode if
        specified. No error handling is performed for an invalid mode to read a file.
    :encoding: str, The encoding format to use with `open()` for a text file object,
        defaults to `'utf-8'`. If `mode` is a binary mode, this must be `None`.
        No error handling is performed for an invalid encoding format.
    
    :show: bool, Whether to open the dialog automatically after creation.
        Defaults to True.
    :\**kwargs: Any other keyword args will be passed to the constructor of 
    `kivy.uix.popup.Popup`.

    The `kivy.uix.filechooser.FileChooserListView` widget is referenced by 
    `self.filechooser`, in case it needs to be customised further."""

    def __init__(self, title:str='Open', size_hint:tuple[float,float]=(0.8,0.8),
            initial_dir:str = ".", rootdir:str = '', multiselect:bool = False, 
            fileobj:bool = False, encoding:Union[str,None]='utf-8',
            action: Union[Callable[[Union[TextIO, list[TextIO]]],Any],
             Callable[[str,str],Any]] = None, mode:str = 'r', 
            show:bool=True, **kwargs):
        # Store various properties
        self.title = title
        self.idir = initial_dir
        self.root = rootdir
        self.multi = multiselect
        self.fileobj = fileobj
        self.mode = mode
        self.enc = encoding
        self.filename = ''
        kwargs.pop('content', None)
 
        if not os.path.isdir(os.path.abspath(self.idir)) :
            self.idir = os.path.abspath('.')
        if not os.path.isdir(os.path.abspath(self.root)) :
            self.root = ''
        if action is None or action is self.dismiss:
            self.action = self.dismiss
        else :
            self.action = self._closeandrun(action)

        # Create GUI
        self.content = BoxLayout(orientation='vertical')
        self.filechooser = FileChooserListView(path=self.idir, rootpath=self.root,
            multiselect=self.multi)
        self.content.add_widget(self.filechooser)
        self.folderlbl = Label(text="  Location : "+self.idir, size_hint_y=None,
            height='35dp')
        self.content.add_widget(self.folderlbl)
        self.filechooser.bind(path=self._updateflbl)
        self.filechooser.bind(selection=self._updatesel)
        self.namefield = TextInput(multiline=False, hint_text="", size_hint_y=None, 
            height='35dp', readonly=True)
        self.content.add_widget(self.namefield)
        self.btns = BoxLayout(spacing='5dp', padding='10dp', size_hint=(0.9, None), 
            height='75dp', pos_hint={'center_x':0.5})
        self.btns.add_widget(Button(text='Open', on_release=self.testvalid))
        self.btns.add_widget(Button(text='Cancel', on_release=self.dismiss))
        self.content.add_widget(self.btns)
        super(OpenFileDialog, self).__init__(title=self.title,
                                             content=self.content,
                                             size_hint=size_hint, **kwargs)
        if show:
            self.open()

    def _closeandrun(self, fn):
        def finish(*args, **kwargs):
            self.dismiss()
            if hasattr(fn, '__call__'):
                fn(*args, **kwargs)
        return finish

    def _updateflbl(self, widget, val):
        self.folderlbl.text = "  Location : "+os.path.abspath(val)

    def _updatesel(self, widget, val):
        if self.multi:
            names = ['"' + os.path.split(addr)[1] + '"' for addr in widget.selection]
            self.namefield.text = ' '.join(names)
        elif len(widget.selection)==1 :
            self.namefield.text = os.path.split(widget.selection[0])[1]

    def testvalid(self, widget):
        """Initiate the open process by checking that some file has been selected
        and that it is accessible by the program. Inform the user in either case
        if there would be an error."""
        if len(self.filechooser.selection) == 0:
            InfoDialog(title='Warning', message='No files have been selected')
            return
        for addr in self.filechooser.selection :
            if not os.path.isfile(addr):
                InfoDialog(title='Error', 
                    message='The specified address {} is invalid'.format(
                    os.path.join(self.filechooser.path, self.namefield.text)))
                return
        self.callfn(True)

    def callfn(self, yn):
        """Call `self.action` with the appropriate arguments, if `yn` is True."""
        if yn :
            cwd = os.getcwd()
            if self.fileobj:
                try :
                    files = []
                    os.chdir(self.filechooser.path)
                    for file in self.filechooser.selection :
                        files.append(open(file, self.mode, encoding=self.enc))
                except:
                    InfoDialog(title='Error', 
                        message='There was an error opening the file {} '.format(
                        os.path.join(self.filechooser.path, self.namefield.text)))
                    Logger.error('OpenFileDialog : {}'.format(sys.exc_info()[2]))
                    os.chdir(cwd)
                    return
                finally:
                    os.chdir(cwd)
                if self.multi :
                    self.action(files)
                elif len(files) != 0 :
                    self.action(files[0])
            else :
                self.action(self.filechooser.path, self.namefield.text)


# ---------------------------- Simulator Widgets--------------------------------

class StencilBox(StencilView, FloatLayout):
    """Class that can prevent canvas drawings on an (infinite)
    `kivy.uix.scatter.ScatterPlane` contained in it as a child being drawn 
    outside its boundary; and prevent touch/click actions from affecting it outside
    the same area as well.
    
    The `StencilView` superclass automatically handles clipping the drawing, and touch
    methods are passed on to children only if they are inside the area by overriding
    the touch methods here.
    
    Reference - https://stackoverflow.com/a/49221416
    """
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return
        return super(StencilBox, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return
        return super(StencilBox, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if not self.collide_point(*touch.pos):
            return
        return super(StencilBox, self).on_touch_up(touch)


# -------------------------- Colour Choosers -----------------------------------

_ColourFormat = Union["tuple[float,float,float,float]",
                      Iterable[float]]

class ColourChooser(BoxLayout):
    """Provides a simple 2-panel widget that allows selection of an RGB or
    RGBA colour via sliders for each component value, alongside a 'live'
    display of the colour formed (with transparency) beside the sliders.
    
    Optional keyword arguments - 

    :transparency: bool, whether to allow a partially transparent (Alpha < 100%)
        colour to be selected. Defaults to True. If it is False, the alpha
        slider will be disabled/unmovable.
        
    Attributes - 
    
    The selected colour can be accessed any time through the following properties
    + :r: float, value of the Red component, in the interval [0,1]
    + :g: float, value of the Green component, in the interval [0,1]
    + :b: float, value of the Blue component, in the interval [0,1]
    + :a: float, value of the Alpha component, in the interval [0,1]
    + :colour: Tuple of the four values `(r, g, b, a)`
    
    `r`, `g`, `b` and `a` support both get and set methods. Their values can be
    updated from a python script to modify the colour selected in the widget.
    `colour` is just a kivy ReferenceListProperty of these.
    Only methods for various bindings are defined here, the UI structure and most
    of the functionality is defined using the `kv` language for this widget."""

    transparency = BooleanProperty(True)
    r = BoundedNumericProperty(0.5, min=0., max=1.,
                               errorhandler=lambda x: 1. if x > 1 else 0.)
    g = BoundedNumericProperty(0.2, min=0., max=1.,
                               errorhandler=lambda x: 1. if x > 1 else 0.)
    b = BoundedNumericProperty(0.8, min=0., max=1.,
                               errorhandler=lambda x: 1. if x > 1 else 0.)
    a = BoundedNumericProperty(1.0, min=0., max=1.,
                               errorhandler=lambda x: 1. if x > 1 else 0.)
    colour = ReferenceListProperty(r, g, b, a)
    red = ObjectProperty(None)
    green = ObjectProperty(None)
    blue = ObjectProperty(None)
    alpha = ObjectProperty(None)
    display = ObjectProperty(None)

    def _update_colour(self, c='', val=None):
        """Change the values of attributes based on slider movement"""
        if val is not None :
            if c is 'r' :
                self.r = val
            elif c is 'g':
                self.g = val
            elif c is 'b':
                self.b = val
            elif c is 'a':
                self.a = val

    # Update the text in the UI based on the colour values set
    # The binding is automatic using kivy's `on_<propname>` ability
    def on_r(self, obj, val):
        self.red.value = int(255*val)
        
    def on_g(self, obj, val):
        self.green.value = int(255*val)
        
    def on_b(self, obj, val):
        self.blue.value = int(255*val)
        
    def on_a(self, obj, val):
        self.alpha.value = int(255*val)

Builder.load_string("""
#:import dp kivy.metrics.dp
<ColourSlider@Slider>:
    min: 0
    max: 255
    step: 1
    value_track: True
    size_hint_x: 0.9

<ColourChooser>:
    red: red
    green: green
    blue: blue
    alpha: alpha
    display: colourdisplay
    # spacing: '20dp'
    pos_hint: {'center_x':0.5, 'center_y':0.5}
    BoxLayout:
        # Left panel, contains the sliders
        id: sliderpanel
        spacing: '5dp'
        orientation: 'vertical'
        padding_x: '20dp'
        Label:
            text: 'Red : {}'.format(int(red.value))
        ColourSlider:
            id: red
            value: 125
            value_track_color: [1,0,0,1]
            on_value: root._update_colour('r', self.value_normalized)
        Label:
            text: 'Green : {}'.format(int(green.value))
        ColourSlider:
            id: green
            value: 50
            value_track_color: [0,1,0,1]
            on_value: root._update_colour('g', self.value_normalized)
        Label:
            text: 'Blue : {}'.format(int(blue.value))
        ColourSlider:
            id: blue
            value: 200
            value_track_color: [0,0,1,1]
            on_value: root._update_colour('b', self.value_normalized)
        Label:
            text: 'Alpha : {}'.format(int(alpha.value))
        ColourSlider:
            id: alpha
            value: 255
            value_track_color: [1,1,1,1]
            disabled: not root.transparency
            on_value: root._update_colour('a', self.value_normalized)
    Label:
        id: colourdisplay
        size_hint: 0.9, 0.9
        width: root.width - sliderpanel.width - dp(20)
        height: root.height - dp(20)
        pos_hint: {'center_x': 0.45, 'center_y': 0.5}
        canvas:
            Rectangle:
                source: 'icons/transparent-bg.jpg'
                pos: self.pos
                size: self.size
            Color:
                rgba: (red.value_normalized, green.value_normalized, \
                       blue.value_normalized, alpha.value_normalized)
            Rectangle:
                pos: self.pos
                size: self.size                
""", filename='cw_ColourChooser.kv')

class ColourChooserPopup(Popup):
    r"""Dialog containing a `ColourChooser` widget with 'Select' and 'Cancel'
    buttons, that can call a function like `InfoDialog` etc after the user
    has selected a colour.
    
    Optional keyword arguments - 
    
    :title: str, Title of the prompt. Defaults to "Colours"
    :size_hint: tuple of 2 floats, Kivy size hint for the dialog. Defaults
        to (0.7, 0.7)
    :colour: tuple of 4 floats, The initial colour that is displayed in the
        dialog when it opens. Defaults to [0.1, 0.8, 0.8, 1] (a slightly dark cyan)
    :transparency: bool, Whether to enable modifying the Alpha value. Defaults to True.
    :action: callable, A function that will be called with one positional argument,
        the selected colour (as a tuple) if the user closes the dialog by pressing
        'Select', else with the argument `None`, if they close it by pressing 'Cancel'.
        No error handling is performed during this callback. `action` defaults to None,
        in which case no function will be called.
    :show: bool, Whether to open the popup automatically after creation.
        Defaults to True.
    :\**kwargs: Any other keyword args will be passed to the constructor of
        `kivy.uix.popup.Popup`
    """

    def __init__(self, title: str = "Colours", 
            size_hint: tuple[float,float] = (0.7, 0.7), 
            colour: _ColourFormat = (0.1, 0.8, 0.8, 1),
            transparency: bool = True, show: bool = True,
            action: Callable[[Union[_ColourFormat, None]],Any] = None,
            **kwargs):
        
        kwargs.pop('content', None)
        self.title = title
        content = BoxLayout(orientation='vertical')
        self.cch = ColourChooser(size_hint=(0.9, 0.9), transparency=transparency)
        self.cch.r, self.cch.g, self.cch.b, self.cch.a = colour
        content.add_widget(self.cch)
        if action is None or action is self.dismiss:
            action = self.dismiss
        else :
            action = self._closeandrun(action)
        btns = BoxLayout(spacing='5dp', padding='10dp',  height='80dp',
                         pos_hint={'center_x':0.5}, size_hint=(0.9, None))
        btns.add_widget(Button(text='Select',
                            on_release=lambda arg : action(tuple(self.cch.colour))))
        btns.add_widget(Button(text='Cancel',
                            on_release=lambda arg : action(None)))
        content.add_widget(btns)
        super(ColourChooserPopup, self).__init__(title=self.title,
                            content=content, size_hint=size_hint, **kwargs)
        if show :
            self.open()

    def _closeandrun(self, fn):
        # Close the dialog, then perform required callback
        def finish(*args, **kwargs):
            self.dismiss()
            if hasattr(fn, '__call__'):
                fn(*args, **kwargs)
        return finish


# ------------------------------ Settings --------------------------------------

class SettingColour(SettingItem):
    """An instance of `kivy.uix.settings.SettingItem` that allows for a
    colour value in a kivy Settings Panel.
    
    The contents of this class are similar to those of 
    `kivy.uix.settings.SettingString`, refer to the kivy source for 
    comparison; except that the popup containing a text field is replaced
    with `ColourChooserPopup`, and the content label's foreground/text colour
    is adjusted to match it.
    """

    popup = ObjectProperty(None, allownone=True)
    cch = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(SettingColour, self).__init__(**kwargs)
        ivalue = [0.1, 0.1, 0.1, 1]
        self.clbl = Label(text='████████████', color=ivalue)
        self.content.add_widget(self.clbl)

    def on_panel(self, instance, value):
        if value is None:
            return
        self.fbind('on_release', self._create_popup)

    def _dismiss(self, *largs):
        if self.cch:
            self.cch.focus = False
        if self.popup:
            self.popup.dismiss()
        self.popup = None

    def _validate(self, instance):
        self._dismiss()
        value = self.cch.colour
        self.value = value
        self.clbl.color = value

    def _create_popup(self, instance):
        # create popup layout
        ccontent = BoxLayout(orientation='vertical', spacing='5dp')
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=ccontent, size_hint=(None, 0.9),
            width=popup_width)

        # create the colourchooser widget
        cch = ColourChooser(size_hint=(0.9, 0.9))
        if len(self.value)==4 and all([x >= 0. for x in self.value]) and \
           all([x <= 1. for x in self.value]) :
            cch.r, cch.g, cch.b, cch.a = self.value
        self.cch = cch

        # construct the content, widget are used as a spacer
        ccontent.add_widget(Widget(size_hint=(0.1, 0.1)))
        ccontent.add_widget(cch)
        ccontent.add_widget(Widget(size_hint=(0.1, 0.1)))
        ccontent.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        ccontent.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()


class SettingPathWRoot(SettingPath):
    """An instance of `kivy.uix.settings.SettingPath` that allows the root
    directory of the kivy file browser associated with it to be customised.
    
    The contents of this class are similar to those of 
    `kivy.uix.settings.SettingPath`, refer to the kivy source for 
    comparison; except that the `FileChooserListView` used to select an
    address uses the value of the token `('app','rootpath')` in the app config
    file as a root directory. 
    Reference - https://kivy.org/doc/stable/api-kivy.app.html#application-configuration.
    If such a setting is not available or there is any error trying to access the
    app's config; then the value of `fallback_root`, given to the constructor
    (defaults to `""`) will be used.
    """

    def __init__(self, fallback_root="", **kwargs):
        self.fallback_root = fallback_root
        super(SettingPathWRoot, self).__init__(**kwargs)
        for w in self.content.children :
            if isinstance(w, Label):
                w.multiline = False
                w.text_size = (2*int(w.width), None)
                w.shorten = True
                w.shorten_from = 'center'
    
    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing=5)
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, 0.9),
            width=popup_width)
        # create the filechooser
        
            # Custom addition to enable choosing rootpath
        try :
            rp = App.get_running_app().config.get('app', 'rootpath')
        except :
            rp = self.fallback_root
            # ---
        
        initial_path = self.value or os.getcwd()
        self.textinput = textinput = FileChooserListView(
            rootpath=rp, size_hint=(1, 1), path=initial_path,
            dirselect=self.dirselect, show_hidden=self.show_hidden)
        textinput.bind(on_path=self._validate)
        
        # construct the content
        content.add_widget(textinput)
        content.add_widget(SettingSpacer())
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)
        
        # all done, open the popup !
        popup.open()


class GravSettings(Settings):
    """Settings class that uses the sidebar interface, and accepts
    ``pathwithroot`` and ``colour`` as valid setting types while adding
    panels from json content."""

    def __init__(self, **kwargs):
        self.interface_cls = InterfaceWithSidebar
        super(GravSettings, self).__init__(**kwargs)
        self.register_type('pathwithroot', SettingPathWRoot)
        self.register_type('colour', SettingColour)


