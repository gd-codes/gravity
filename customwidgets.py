
from kivy.uix.settings import *
from kivy.uix.settings import InterfaceWithSidebar
from kivy.uix.settings import SettingSpacer
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.stencilview import StencilView
from kivy.uix.scrollview import ScrollView
from kivy.uix.scatter import Scatter
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
from kivy.clock import Clock

import os, sys, re

__all__ = ['InfoDialog', 'ColourChooser', 'ColourChooserPopup',
           'GravSettings', 'QuestionDialog', 'SettingSpacer',
           'SaveFileDialog', 'OpenFileDialog', 'WrapLabel', 'BGLabel',
           'StencilBox', 'Transformer', 'NumEntry', 'ContentDialog']

#chars = string.ascii_lowercase + string.ascii_digits

class WrapLabel(Label):
    pass
Builder.load_string("""
<WrapLabel>:
    #size_hint_y: None
    text_size: self.width, None
    #height: self.texture_size[1]
""")

class BGLabel(Label):
    
    bgcolour = ListProperty([0.5, 0.5, 0.5, 1])

    def __init__(self, **kwargs):
        self.bgcolour = kwargs.pop('bgcolour', [0.5,0.5,0.5,1])
        super(BGLabel, self).__init__(**kwargs)

Builder.load_string("""
<BGLabel>:
    canvas.before:
        Color:
            rgba: root.bgcolour
        Rectangle:
            size: self.size
            pos: self.pos
""")

class NumEntry(TextInput):

    autovalidate = BooleanProperty(True)
    valid = BooleanProperty(False)
    ontext_callbacks = ListProperty([])

    def __init__(self, **kwargs):
        super(NumEntry, self).__init__(**kwargs)
        self.multiline = False
        self.write_tab = False

    def insert_text(self, substring, from_undo=False):
        if re.search("[^\d\.\+\-eE]", substring):
            return super(NumEntry, self).insert_text('', from_undo=from_undo)
        return super(NumEntry, self).insert_text(substring, from_undo=from_undo)

    def on_text(self, widget, text):
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
        if val:
            self.foreground_color = [0,0,0,1]
        else:
            self.foreground_color = [1,0,0,1]

    def get(self):
        try:
            return float(self.text)
        except ValueError:
            return None

    def on_readonly(self, widget, val):
        if val:
            self.background_color = [0.7,0.71,0.7,1]
        else:
            self.background_color = [1,1,1,1]


# ------------------- Info Dialog & Question Dialog ----------------------------
class InfoDialog(Popup):

    def __init__(self, **kwargs):
        self.title = kwargs.pop('title', 'Info')
        self.message = kwargs.pop('message', '')
        kwargs.pop('content', None)
        sh = kwargs.pop('size_hint', (0.5,0.5))
        action = kwargs.pop('action', None)
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
                                         size_hint=sh, **kwargs)
        self.open()

    def _closeandrun(self, fn):
        def finish(*args, **kwargs):
            self.dismiss()
            fn(*args, **kwargs)
        return finish

class QuestionDialog(Popup):

    def __init__(self, **kwargs):
        self.title = kwargs.pop('title', 'Confirm')
        self.question = kwargs.pop('question', '')
        kwargs.pop('content', None)
        sh = kwargs.pop('size_hint', (0.5,0.5))
        acn = kwargs.pop('action', None)
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=self.question, size_hint=(0.9, 0.9)))
        if acn is None or acn is self.dismiss:
            action = self._pass
        else :
            action = self._closeandrun(acn)
        btns = BoxLayout(spacing='5dp', padding='10dp',
                         size_hint=(0.9, None), height='75dp',
                         pos_hint={'center_x':0.5})
        btns.add_widget(Button(text='Yes', on_release=lambda arg: action(True)))
        btns.add_widget(Button(text='No', on_release=lambda arg: action(False)))
        content.add_widget(btns)
        super(QuestionDialog, self).__init__(title=self.title, content=content,
                                         size_hint=sh, **kwargs)
        self.open()

    def _closeandrun(self, fn):
        def finish(*args, **kwargs):
            self.dismiss()
            fn(*args, **kwargs)
        return finish

    def _pass(self, *args, **kwargs):
        # Do nothing
        self.dismiss()


class ContentDialog(Popup):

    _classes = {'Label':Label, 'Image':Image, 'Widget':Widget,
        'Separator':SettingSpacer, 'WrapLabel':WrapLabel,
        'BGLabel':BGLabel, 'AsyncImage':AsyncImage}

    def __init__(self, widgets, **kwargs):
        self.title = kwargs.pop('title', 'Info')
        kwargs.pop('content', None)
        sh = kwargs.pop('size_hint', (0.5,0.5))
        action = kwargs.pop('action', None)
        start = kwargs.pop('show', True)
        if action is None or action is self.dismiss:
            action = self.dismiss
        else :
            action = self._closeandrun(action)
        ori = kwargs.pop('orientation', 'vertical')
        p, s = kwargs.pop('padding', 0), kwargs.pop('spacing', 0)

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
                                         size_hint=sh)
        self.widgetarea = BoxLayout(orientation=ori,
            padding=p, spacing=s, size_hint=(1,None),)
        self.scrollarea.add_widget(self.widgetarea)
        for w in widgets:
            try:
                c = w.pop('class', None)
                if c not in self._classes:
                    Logger.warning(f"ContentDialog : Widget {c} is not supported")
                    continue
                wgt = self._classes[c](**w)
                wgt.size_hint = (1, None)
                self.widgetarea.add_widget(wgt)
            except Exception as err:
                Logger.error(f"ContentDialog : Error creating widget {w}", 
                    exc_info = str(err))
                continue
        #self.widgetarea.height = self.widgetarea.minimum_height
        if start:
            self.open()

    def _closeandrun(self, fn):
        def finish(*args, **kwargs):
            self.dismiss()
            fn(*args, **kwargs)
        return finish

    def open(self):
        super(ContentDialog, self).open()
        self._updatesize()

    def _updatesize(self):
        self.widgetarea.height = 10
        for x in self.widgetarea.children:
            if any([isinstance(x, c) for c in \
                (Label, Image, WrapLabel, AsyncImage, BGLabel)]):
                x.width = 0.95 * self.width
                x.texture_update()
                x.height = x.texture_size[1]
            self.widgetarea.height += x.height + self.widgetarea.spacing

# -------------------------- Save Dialog ---------------------------------------
class SaveFileDialog(Popup):

    def __init__(self, action=None, **kwargs):
        # Store various properties
        self.title = kwargs.pop('title', 'Save As')
        self.idir = kwargs.pop('initial_dir', os.path.abspath('.'))
        self.root = kwargs.pop('rootdir', '')
        start = kwargs.pop('show', True)
        self.ext = kwargs.pop('ext', '')
        self.fileobj = kwargs.pop('fileobj', False)
        self.mode = kwargs.pop('mode', 'w') 
        self.enc = kwargs.pop('encoding', 'utf-8')
        kwargs.pop('content', None)
        sh = kwargs.pop('size_hint', (0.8, 0.8))
        self.filename = ''
        self.content = BoxLayout(orientation='vertical')
        # Ensure that given paths exist
        if not os.path.isdir(os.path.abspath(self.idir)) :
            self.idir = os.path.abspath('.')
        if not os.path.isdir(os.path.abspath(self.root)) :
            self.root = ''
        # Decorate callback 
        if action is None or action is self.dismiss:
            self.action = self._pass
        else :
            self.action = self._closeandrun(action)

        # Create GUI
        self.filechooser = FileChooserListView(path=self.idir, rootpath=self.root)
        self.content.add_widget(self.filechooser)
        self.folderlbl = Label(text="  Location : "+self.idir, size_hint_y=None, height='35dp')
        self.content.add_widget(self.folderlbl)
        self.filechooser.bind(path=self._updateflbl)
        self.filechooser.bind(selection=self._updatesel)
        self.namefield = TextInput(multiline=False, hint_text="Enter a filename", text="Untitled"+self.ext,
                                   size_hint_y=None, height='35dp', on_text_validate=self.testvalid)
        self.content.add_widget(self.namefield)
        self.btns = BoxLayout(spacing='5dp', padding='10dp', size_hint=(0.9, None), height='75dp', pos_hint={'center_x':0.5})
        self.btns.add_widget(Button(text='Save', on_release=self.testvalid))
        self.btns.add_widget(Button(text='Cancel', on_release=self.dismiss))
        self.content.add_widget(self.btns)
        super(SaveFileDialog, self).__init__(title=self.title,
                                             content=self.content,
                                             size_hint=sh, **kwargs)
        if start:
            self.open()

    def _pass(self, *args, **kwargs):
        # Do nothing
        self.dismiss()

    def _closeandrun(self, fn):
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
            # Check if filename is valid by trying to create the file
            # If a file object needs to be returned instead of the path, return this
            # Otherwise close & delete it, then return the path
            tmp = open(self.filename, 'x', encoding=self.enc)
            if self.fileobj :
                self.callfn(True, tmp)
                return
            tmp.close()
            os.remove(self.filename)
        
        except FileExistsError:
            QuestionDialog(question='"{}" already exists. Replace it ?'.format(self.filename), action=self.callfn)
            return
        except :
            # Invalid name or path
            Logger.error('SaveFileDialog : {}'.format(sys.exc_info()[2]))
            InfoDialog(title='Error', message='The specified address  {} is invalid'.format(
                os.path.join(self.filechooser.path, self.namefield.text)))
            os.chdir(cwd)
            return
        finally :
            os.chdir(cwd)
        self.callfn(True)

    def callfn(self, yn, obj=None):
        if yn :
            if self.fileobj:
                if obj is not None:
                    self.action(obj)
                else :
                    self.action(open(self.filename,self.mode,encoding=self.enc))
            else :
                self.action(self.filechooser.path, self.namefield.text)


# -------------------------- Open Dialog ---------------------------------------
class OpenFileDialog(Popup):

    def __init__(self, action=None, **kwargs):
        # Store various properties
        self.title = kwargs.pop('title', 'Open')
        self.idir = kwargs.pop('initial_dir', os.path.abspath('.'))
        self.root = kwargs.pop('rootdir', '')
        start = kwargs.pop('show', False)
        self.multi = kwargs.pop('multiselect', False)
        self.fileobj = kwargs.pop('fileobj', False)
        self.mode = kwargs.pop('mode', 'r')
        self.enc = kwargs.pop('encoding', 'utf-8')
        kwargs.pop('content', None)
        sh = kwargs.pop('size_hint', (0.8, 0.8))
        self.filename = ''
        self.content = BoxLayout(orientation='vertical')
        if not os.path.isdir(os.path.abspath(self.idir)) :
            self.idir = os.path.abspath('.')
        if not os.path.isdir(os.path.abspath(self.root)) :
            self.root = ''
        if action is None or action is self.dismiss:
            self.action = self._pass
        else :
            self.action = self._closeandrun(action)

        # Create GUI
        self.filechooser = FileChooserListView(path=self.idir, rootpath=self.root, multiselect=self.multi)
        self.content.add_widget(self.filechooser)
        self.folderlbl = Label(text="  Location : "+self.idir, size_hint_y=None, height='35dp')
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
                                             size_hint=sh, **kwargs)
        if start:
            self.open()

    def _pass(self, *args, **kwargs):
        # Do nothing, absorb any arguments passed
        self.dismiss()

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
        if len(self.filechooser.selection) == 0:
            InfoDialog(title='Warning', message='No files have been selected')
            return
        for addr in self.filechooser.selection :
            if not os.path.isfile(addr):
                InfoDialog(title='Error', message='The specified address {} is invalid'.format(
                    os.path.join(self.filechooser.path, self.namefield.text)))
                return
        self.callfn(True)

    def callfn(self, yn):
        if yn :
            cwd = os.getcwd()
            if self.fileobj:
                try :
                    files = []
                    os.chdir(self.filechooser.path)
                    for file in self.filechooser.selection :
                        files.append(open(file, self.mode, encoding=self.enc))
                except:
                    InfoDialog(title='Error', message='There was an error opening address {} '.format(
                        os.path.join(self.filechooser.path, self.namefield.text)))
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


class Transformer(Scatter):

    x_coord = NumericProperty(0)
    y_coord = NumericProperty(0)

    def __init__(self, **kwargs):
        super(Transformer, self).__init__(**kwargs)

    def on_transform_with_touch(self, touch):
        print(self.transform)
        super(Transformer, self).on_transform_with_touch(touch)
        print(self.transform, '\n\n')

# -------------------------- Colour Choosers -----------------------------------
class ColourChooser(BoxLayout):

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
        if val is not None :
            if c is 'r' :
                self.r = val
            elif c is 'g':
                self.g = val
            elif c is 'b':
                self.b = val
            elif c is 'a':
                self.a = val

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
                source: 'icons/transparent.jpg'
                pos: self.pos
                size: self.size
            Color:
                rgba: (red.value_normalized, green.value_normalized, blue.value_normalized, alpha.value_normalized)
            Rectangle:
                pos: self.pos
                size: self.size                
""")

class ColourChooserPopup(Popup):

    def __init__(self, action=None, **kwargs):
        kwargs.pop('content', None)
        self.title = kwargs.pop('title', "Colours")
        sh = kwargs.pop('size_hint', (0.7, 0.7))
        icolour = kwargs.pop('colour', [0.1, 0.8, 0.8, 1])
        trp = kwargs.pop('transparency', True)
        start = kwargs.pop('show', False)
        content = BoxLayout(orientation='vertical')
        self.cch = ColourChooser(size_hint=(0.9, 0.9), transparency=trp)
        self.cch.r, self.cch.g, self.cch.b, self.cch.a = icolour
        content.add_widget(self.cch)
        if action is None or action is self.dismiss:
            action = self._pass
        else :
            action = self._closeandrun(action)
        btns = BoxLayout(spacing='5dp', padding='10dp',  height='80dp',
                         pos_hint={'center_x':0.5}, size_hint=(0.9, None))
        btns.add_widget(Button(text='Select',
                               on_release=lambda arg : action(self.cch.colour)))
        btns.add_widget(Button(text='Cancel',
                               on_release=lambda arg : action(None)))
        content.add_widget(btns)
        super(ColourChooserPopup, self).__init__(title=self.title,
                                    content=content, size_hint=sh, **kwargs)
        if start :
            self.open()

    def _closeandrun(self, fn):
        def finish(*args, **kwargs):
            self.dismiss()
            if hasattr(fn, '__call__'):
                fn(*args, **kwargs)
        return finish

    def _pass(self, *args, **kwargs):
        self.dismiss()


# ------------------------------ Settings --------------------------------------

class SettingColour(SettingItem):
    # This class' format is similar to SettingString

    popup = ObjectProperty(None, allownone=True)
    cch = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(SettingColour, self).__init__(**kwargs)
        ivalue = [0.1, 0.1, 0.1, 1]
        '''self.clbl = Button(text=' ', size_hint=(None, 0.8), width='100dp', 
                           pos_hint={'center_x':self.content.center_x},
                           background_color=ivalue)
                           #on_release=self._create_popup)'''
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
        '''with self.clbl.canvas :
            Color(*self.value)
            Rectangle(size=self.clbl.size, pos=self.clbl.pos)'''
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

    def __init__(self, **kwargs):
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
        rp = App.get_running_app().config.get('app', 'rootpath')
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

    def __init__(self, **kwargs):
        self.interface_cls = InterfaceWithSidebar
        super(GravSettings, self).__init__(**kwargs)
        self.register_type('pathwithroot', SettingPathWRoot)
        self.register_type('colour', SettingColour)



if __name__ == '__main__':
    class TestApp1(App):
        def build(self):
            return ColourChooser()

    TestApp1().run()
