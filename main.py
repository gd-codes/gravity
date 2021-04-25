
"""
Gravity - Simulation of gravitation between point masses in 2D space
"""
# gravityapp.py
# User interface and animation with kivy
# Gautam D
# May - June 2020

import kivy
kivy.require('1.11.0')
import os, sys, math, json, time
from datetime import datetime
import traceback, random
import sympy

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import *
from kivy.graphics import *
from kivy.graphics.instructions import InstructionGroup
from kivy.core.image import Image
from kivy.logger import Logger
from kivy.config import Config
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

from customwidgets import *


# ************************* Mathematical functions *****************************

def to_cartesian(m, a, rad=False):
    """Convert 2D polar coords (magnitude `m`, angle `a`) to cartesian (x,y)
    a is in degrees, unless `rad=True`"""
    if rad :
        x, y =  m * math.cos(a), m * math.sin(a)
    else :
        x, y = m * math.cos(math.radians(a)), m * math.sin(math.radians(a))
    return (x, y)

def to_polar(x, y, rad=False):
    """Convert 2D cartesian coords (`x`, `y`) to polar (mag, angle)
    angle is returned in degrees, unless `rad=True`"""
    m = math.hypot(x, y)
    a = math.degrees(math.atan(y/x)) if x != 0. else 90
    if x < 0 : a += 180
    elif x == 0. and y < 0: a = 270
    elif x > 0 and y < 0: a += 360
    if rad :
        a *= math.pi / 180.
    return (m, a)

def hexcolour(c):
    """Convert a list/tuple `c` of floats in range [0,1] 
    representing a colour to hex string `#rrggbb` format"""
    return '#' + ''.join([hex(int(i*255))[2:].rjust(2,'0') for i in c])


class PlanetObject :

    def __init__(self, system=None, m=1, x=0, y=0, vx=0, vy=0,
                 color=[1,1,1,1], radius=5, trail=100, idx="", polar=False):
        self.system = system
        self.mass = math.fabs(m)
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.ax, self.ay = 0, 0
        self.colour = color
        self.radius = radius
        self.trail = trail
        self.positions = [(self.x, self.y)]*2
        self.has_collided = False
        self.idx = str(idx)
        self.polar = polar
        self.system.add_obj(self)
        self.info = BGLabel(size_hint=(None, None), bgcolour=[0.2,0.2,0.2,0.5],
                            width='200dp', height='80dp', color=[1,1,1,1],
                            markup=True, text=str(self), font_size='11sp')
        #self.info.height = self.info.minimum_height
        Logger.info(f"Simulation : New object - ({self.idx}, {hexcolour(self.colour)}, \
M={self.mass}, R={self.radius}, pos=({self.x}, {self.y}), vel=({self.vx}, {self.vy}), \
trail={self.trail}, polar={self.polar}")

    def _neatpos(self, p1, p2):
        global to_polar
        if self.polar :
            d, a = to_polar(p1, p2)
            return (round(d,5), round(a,5))
        else :
            return (round(p1, 5), round(p2, 5))

    def force(self, other):
        r = math.hypot(self.x-other.x, self.y-other.y)
        if self.system.collisions and \
           r <= self.system.rf * (self.radius + other.radius) and \
           not self.has_collided and not other.has_collided :
            self.collide(other)
            return (0, 0)
        try :
            signx = 1 if other.x > self.x else -1
            _ax = signx*self.system.G*other.mass*math.fabs(self.x-other.x)/r**3
            signy = 1 if other.y > self.y else -1
            _ay = signy*self.system.G*other.mass*math.fabs(self.y-other.y)/r**3
        except ZeroDivisionError :
            Logger.warning(f'Simulation: objects {self.idx} and {other.idx} are overlapping !')
            if self.vx-other.vx == 0 and self.vy-other.vy == 0:
                Logger.warning('Simulation: Shifting the coinciding bodies to avoid overlap')
                self.vx += 1
                other.vy += 1
            return (0, 0)
        return (_ax, _ay)

    def update(self, dt):
        try :
            net_ax, net_ay = 0, 0
            for body in self.system.all:
                if body is not self :
                    _ax, _ay = self.force(body)
                    net_ax += _ax
                    net_ay += _ay
            self.ax, self.ay = net_ax, net_ay
            
            if self.system.calc_num == 0 :
                self.vx += dt/2 * self.ax
                self.vy += dt/2 * self.ay
            else :
                self.vx += dt * self.ax
                self.vy += dt * self.ay

            if self.trail :
                lx, ly = self.positions[-1]
                if math.hypot(self.x-lx, self.y-ly) >= self.system.tpdist :
                    self.positions.append((self.x, self.y))
                    self.system.totalpts += 1
                if self.trail >= 0 and len(self.positions) > self.trail :
                    self.positions.pop(0)
                    self.system.totalpts -= 1
            self.x += dt * self.vx
            self.y += dt * self.vy
            if abs(self.x)>self.system.bound or abs(self.y)>self.system.bound:
                self.system.all.remove(self)
                self.system.runaway.append(self)
                self.info.text = f"""    <{self.idx}>
Mass : {self.mass}        Radius : {self.radius}
Position {'(Dist, Angle)' if self.polar else '(X, Y)'} : {self._neatpos(self.x, self.y)}
    <- Escaped ->"""
                Logger.info(f'Simulation : Object {self.idx} has crossed the boundary')
            self.info.text = str(self)
        except OverflowError :
            Logger.warning(f'Simulation : Overflow encountered for object {self.idx}!')
            self.system.all.remove(self)
            self.system.runaway.append(self)
            InfoDialog(title='Overflow Error',
                message=f"The object at \n{str(self)}\nwas removed from the simulation.")

    def collide(self, other):
        if self.system is not other.system :
            Logger.error('Simulation: Cannot collide 2 bodies in different systems')
            return
        new_m = self.mass + other.mass
        new_x = (self.mass*self.x + other.mass*other.x) / new_m
        new_y = (self.mass*self.y + other.mass*other.y) / new_m
        new_vx = self.system.vf * (self.mass*self.vx + other.mass*other.vx) / new_m
        new_vy = self.system.vf * (self.mass*self.vy + other.mass*other.vy) / new_m
        r1, g1, b1, a1 = self.colour
        r2, g2, b2, a2 = other.colour
        c = ((self.mass*r1+other.mass*r2)/new_m,
             (self.mass*g1+other.mass*g2)/new_m,
             (self.mass*b1+other.mass*b2)/new_m,
             (self.mass*a1+other.mass*a2)/new_m)
        if self.system.autoradius :
            new_r = max(1, round(math.sqrt(new_m) / self.system.r_const))
        else :
            new_r = max([self.radius, other.radius])
        tr = max(self.trail, other.trail)            
        self.has_collided = True
        other.has_collided = True
        nid = '+'.join((self.idx, other.idx))
        self.system.all.remove(self)
        other.system.all.remove(other)
        self.system.collided.append(self)
        other.system.collided.append(other)
        self.info.text = f"""    <{self.idx}>
Mass : {self.mass}        Radius : {self.radius}
Position {'(r, '+chr(952)+')' if self.polar else '(X, Y)'} : {self._neatpos(self.x, self.y)}
    <- Collided ->"""
        other.info.text = f"""    <{other.idx}>
Mass : {other.mass}        Radius : {other.radius}
Position {'(r, '+chr(952)+')' if other.polar else '(X, Y)'} : {other._neatpos(other.x, other.y)}
    <- Collided ->"""
        Logger.info(f'Simulation : Objects {self.idx} and {other.idx} have collided')
        p = App.get_running_app().config.getboolean('obj', 'polar')
        return PlanetObject(self.system, new_m, new_x, new_y, new_vx, new_vy,
                            c, new_r, tr, nid, p)

    def __str__(self):
        return f"""    <{self.idx}>
Mass : {self.mass}        Radius : {self.radius}
Position {'(r, '+chr(952)+')' if self.polar else '(X, Y)'} : {self._neatpos(self.x, self.y)}
Velocity {'(|v|, '+chr(952)+')' if self.polar else '(X, Y)'} : {self._neatpos(self.vx, self.vy)}
Acceleration {'(|a|, '+chr(952)+')' if self.polar else '(X, Y)'} : {self._neatpos(self.ax, self.ay)}"""


class GravSystem :

    def __init__(self, const_G=1, const_dt=0.01, bound=10000, f_calc=50,
                 random=False, autoradius=True, r_const=3, collision=True,
                 rf=1, vf=1, tpdist=1):
        self.G = const_G
        self.dt = const_dt
        self.bound = abs(bound)
        self.freq = abs(f_calc)
        self.random = random
        self.autoradius = autoradius
        self.r_const = r_const
        self.collisions = collision
        self.rf = rf
        self.vf = vf
        self.tpdist = tpdist

        self.all = list()
        self.collided = list()
        self.runaway = list()
        self.totalpts = 0
        self.calc_num = 0
        self.simtime = 0.0

    def add_obj(self, o):
        self.all.append(o)

    def update(self, delta):
        for p in self.all :
            p.update(delta)
        self.calc_num += 1
        self.simtime += delta



# ********************************* Interface **********************************

class PlanetInput(BoxLayout):

    idlbl = ObjectProperty(None)
    colour = ObjectProperty(None)
    mass = ObjectProperty(None)
    radius = ObjectProperty(None)
    trail = ObjectProperty(None)
    pos0 = ObjectProperty(None)
    pos1 = ObjectProperty(None)
    vel0 = ObjectProperty(None)
    vel1 = ObjectProperty(None)
    close = ObjectProperty(None)

    index = NumericProperty(0)
    inicolour = ListProperty([0.5, 0.4, 0.3, 1])
    t_scale = NumericProperty(50)
    autoradius = BooleanProperty(True)
    usepolar = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super(PlanetInput, self).__init__(**kwargs)
        self.app = App.get_running_app()
        self.cnf = self.app.config
        self.autoradius = bool(self.app.config.getint('obj', 'autoradius'))
        self.usepolar = bool(self.app.config.getint('obj', 'polar'))

    def setcolour(self, colour):
        if colour is not None :
            self.colour.background_color = colour
            self.idlbl.bgcolour = colour
            avg = colour[3] * sum(colour[:3])/3.
            self.idlbl.color = (0,0,0,1) if avg > 0.5 else (1,1,1,1)

    def find_rad(self):
        if self.autoradius:
            try:
                m = int(self.mass.text)
                k = self.cnf.getint('obj', 'r_const')
                r = max(1, round(math.sqrt(m) / k))
                self.radius.text = str(r)
            except (ValueError, ZeroDivisionError) :
                pass


class Simulator(BoxLayout):

    simstateicon = StringProperty("icons/cancelw.png")
    simstatetext = StringProperty("Not Running")
    simstatecolour = ListProperty([0.9,0.9,0.9,1])
    active = BooleanProperty(False)
    paused = BooleanProperty(False)
    xpos = NumericProperty(0)
    ypos = NumericProperty(0)
    infovis = BooleanProperty(False)

    simcontrols = ObjectProperty(None)
    scatter = ObjectProperty(None)
    viewer = ObjectProperty(None)
    ppbtn = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(Simulator, self).__init__(**kwargs)
        self.system = None
        self.cnf = App.get_running_app().config
        self.space = None
        self.interactions = dict([(a, False) for a in \
                                  ('l','u','d','r','zi','zo','tc','ta')])
        self.calc_event = None
        self.draw_event = None
        self.details = BGLabel(size_hint=(None, None), bgcolour=[0.2,0.2,0.2,0.0],
                        width='250dp', height='350dp', color=[1,1,1,1],
                        markup=True, pos_hint={'top':1, 'left':0}, font_size='15sp',
                        halign='left', valign='top', padding=('10dp','10dp'))
        self.details.text_size = self.details.size
        self.start_time = 0.0

    def _changesystemoffset(self):
        if self.system is not None :
            m = list(self.scatter.transform.get())
            self.xpos = round(self.viewer.width/2 - m[12], 4)
            self.ypos = round(self.viewer.height/2 + 1.5*self.simcontrols.height - m[13], 4)
            if self.infovis :
                for p in self.system.all + self.system.collided + \
                    self.system.runaway :
                    p.info.pos = self.scatter.to_parent(p.x, p.y)

    def begin(self, gravsystem):
        Logger.info('Simulation : Beginning the simulation')
        self.active = True
        self.system = gravsystem
        self.bound = self.cnf.getint('sim', 'bound')
        self.space = Widget(size_hint=(None, None),
                            width = 2*self.bound + 1,
                            height = 2*self.bound + 1,
                            center=(0,0))
        self.scatter.clear_widgets()
        self.viewer.clear_widgets()
        self.scatter.add_widget(self.space)
        self.viewer.add_widget(self.scatter)
        self.drawaxes = InstructionGroup()
        self.drawaxes.add(Color(rgba=[1,1,1,0.8]))
        self.drawaxes.add(Line(points=[-self.bound, 0, self.bound, 0],
                               dash_length=5, dash_offset=5))
        self.drawaxes.add(Line(points=[0, -self.bound, 0, self.bound],
                               dash_length=5, dash_offset=5))
        self.drawaxes.add(Line(points=[self.bound, self.bound, self.bound,
                        -self.bound, -self.bound, -self.bound, -self.bound,
                        self.bound, self.bound, self.bound], width=3))
        self.drawaxes.add(Color(rgba=[1,1,1,0.4]))
        for i in range(-self.bound, self.bound, 100):
            self.drawaxes.add(Line(points=[i, self.bound, i, -self.bound],
                                   dash_length=2,dash_offset=5))
            self.drawaxes.add(Line(points=[self.bound, i, -self.bound, i],
                                   dash_length=2,dash_offset=5))
        self.start_time = time.time()
        self.play()
        Clock.schedule_once(self._beginvieweradjust)

    def _beginvieweradjust(self, t):
        self.translate_origin()
        ix, iy, iz, ir = self.cnf.getfloat('anim', 'ini_x'), \
                 self.cnf.getfloat('anim', 'ini_y'), \
                 self.cnf.getfloat('anim', 'ini_z')/100.0, \
                 self.cnf.getfloat('anim', 'ini_r')
        self.scatter.transform.translate(ix, iy, 0)
        self.xpos, self.ypos = ix, iy
        self.scatter.scale = iz
        self.scatter.rotation = ir

    def play(self):
        self.calcintv = 1.0 / self.cnf.getint('sim', 'f_calc')
        self.drawintv = 1.0 / self.cnf.getint('anim', 'f_draw')
        self.bgc = [float(x) for x in \
                    self.cnf.get('anim', 'bgcolor').strip('['
                        ).strip(']').replace(' ','').split(',')]
        self.axvis = self.cnf.getboolean('anim', 'ax_visible')
        self.ms = self.cnf.getint('anim', 'move_step')
        self.zs = 1.0 + self.cnf.getfloat('anim', 'zoom_step') / 100.0
        self.ts = self.cnf.getint('anim', 'turn_step')

        self.simstatetext = "Running..."
        self.simstatecolour = [0.1, 0.7, 0.1, 1]
        self.simstateicon = "icons/clock-check-outlinew.png"
        self.ppbtn.state = 'normal'
        self.paused = False
        
        self.calc_event = Clock.schedule_interval(self.calculate_loop,
                                                  self.calcintv)
        self.draw_event = Clock.schedule_interval(self.graphic_loop,
                                                  self.drawintv)
        Logger.info(f"Simulation : Now Playing... Time={str(datetime.now())}, \
Calc. Inter={self.calcintv}, Draw. inter={self.drawintv}")

    def calculate_loop(self, dt=0.01):
        if self.system.random :
            delta = dt/self.calcintv * self.system.dt
        else :
            delta = self.system.dt
        try :
            self.system.update(delta)
        except Exception as err:
            Logger.warning('Simulation : Calculation error', exc_info=str(err))
        if len(self.system.all) == 0 :
            Logger.info('Simulation : No more active objects remaining !')
            InfoDialog(title='Simulation ended',
                       message="No more active objects remaining !")
            self.stop()
        if self.infovis :
            self.details.text = f"""[size=28][b] Gravity Simulation [/b][/size]\n
Calculations completed : {self.system.calc_num}
Previous time interval : {round(delta, 5)}
Run time (secs): {time.time()-self.start_time:.5f}
Time in-simulation   : {round(self.system.simtime, 5)}\n
Number of objects 
        Active : {len(self.system.all)}
        Collided : {len(self.system.collided)}
        Escaped : {len(self.system.runaway)}\n
Viewer size : {self.viewer.size}
Looking at (X,Y) : {(self.xpos, self.ypos)}
Scale : {str(round(self.scatter.scale*100, 2)) + ' %'}
Rotation : {str(round(self.scatter.rotation, 1)) + ' °'}
"""        

    def graphic_loop(self, dt=0.05, usecanvas=None):
        base = usecanvas if usecanvas else self.space.canvas
        base.clear()
        with base :
            Color(rgba=self.bgc)
            bg = Rectangle(size=self.space.size, pos=self.space.pos)
            if self.axvis :
                base.add(self.drawaxes)
            
            for p in self.system.collided + self.system.runaway:
                Color(rgba=p.colour)
                Line(points=p.positions)
                Line(points=[p.x+5, p.y+5, p.x-5, p.y-5, p.x, p.y,
                             p.x-5, p.y+5, p.x+5, p.y-5], width=2)
                if self.infovis :
                    p.info.pos = self.scatter.to_parent(p.x, p.y)
                    if p.info not in self.viewer.children :
                        self.viewer.add_widget(p.info)
            for o in self.system.all :
                Color(rgba=o.colour)
                Line(points=o.positions)
                Ellipse(size=(2*o.radius, 2*o.radius),
                        pos=(o.x-o.radius, o.y-o.radius))
                if self.infovis :
                    o.info.pos = tuple(map(int, self.scatter.to_parent(o.x, o.y)))
                    if o.info not in self.viewer.children :
                        self.viewer.add_widget(o.info)

    def pause(self):
        self.simstatetext = "Paused"
        self.simstatecolour = [0.8, 0.1, 0.1, 1]
        self.simstateicon = "icons/timer-sandw.png"
        self.ppbtn.state = 'down'
        if self.calc_event is not None :
            self.calc_event.cancel()
        if self.draw_event is not None :
            self.draw_event.cancel()
        self.calc_event, self.draw_event = None, None
        Logger.info(f'Simulation : Paused... Time={str(datetime.now())}')
        self.paused = True

    def playpause(self, state):
        if self.active :
            if state == 'down':
                self.pause()
            elif state == 'normal':
                self.play()

    def showhidedata(self, state):
        self.infovis = True if state == 'down' else False
        if not self.infovis :
            self.viewer.clear_widgets()
            self.viewer.add_widget(self.scatter)
        elif self.infovis :
            if self.details not in self.viewer.children:
                self.viewer.add_widget(self.details)

    def stop(self):
        Logger.info(f'Simulation : Stopping simulation {str(datetime.now())}')
        if self.calc_event is not None :
            self.calc_event.cancel()
        if self.draw_event is not None :
            self.draw_event.cancel()
        self.calc_event, self.draw_event = None, None
        self.active = False
        self.ppbtn.state = 'normal'
        self.simstatetext = "Not Running"
        self.simstatecolour = [0.9, 0.9, 0.9, 1]
        self.simstateicon = "icons/cancelw.png"
        

    def translate_origin(self):
        if self.active and isinstance(self.space, Widget):
            m = list(self.scatter.transform.get())
            self.scatter.transform.translate(-m[12], -m[13], 0)
            self.scatter.transform.translate(self.size[0]/2, self.size[1]/2, 0)
            self.xpos, self.ypos = 0, 0

    def translate_left(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.transform.translate(-self.ms, 0, 0)
            self.xpos += self.ms

    def translate_right(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.transform.translate(self.ms, 0, 0)
            self.xpos -= self.ms

    def translate_up(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.transform.translate(0, self.ms, 0)
            self.ypos -= self.ms

    def translate_down(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.transform.translate(0, -self.ms, 0)
            self.ypos += self.ms

    def zoom_in(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.scale *= self.zs

    def zoom_out(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.scale /= self.zs

    def zoom_normal(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.scale = 1.0

    def rotate_cw(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.rotation -= self.ts

    def rotate_anticw(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.rotation += self.ts

    def rotate_normal(self):
        if self.active and isinstance(self.space, Widget):
            self.scatter.rotation = 0.0

    def delete(self):
        self.space.canvas.clear()
        for p in self.system.collided + self.system.runaway:
            if len(p.positions) > 4:
                p.positions = p.positions[-4:]
        for o in self.system.all:
            if len(o.positions) > 4:
                o.positions = o.positions[-4:]

    def screenshot(self):
        auto = self.cnf.getboolean('app', 'autosc')
        if auto :
            path = self.cnf.get('app', 'scpath')
            fname = datetime.now().strftime("Gravity Screenshot %Y-%m-%d %h,%m,%s.png")
            self._savescshot(path, fname)
        else:
            self.pause()
            SaveFileDialog(rootdir=self.cnf.get('app', 'rootpath'), show=True, 
                action=self._savescshot, ext='.png')
            
    def _savescshot(self, path, fname):
        if self.cnf.getboolean('app','fullsc'):
            fbo = Fbo(size=self.space.size)
            self.graphic_loop(usecanvas=fbo)
            i = Image(fbo.texture)
        else:
            i = self.viewer.export_as_image()
        i.save(os.path.join(path, fname))


class Calculators(BoxLayout):

    cf_G = ObjectProperty(None)
    cf_M = ObjectProperty(None)
    cf_R = ObjectProperty(None)
    cf_v_orb = ObjectProperty(None)
    cf_v_esc = ObjectProperty(None)
    cf_T = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super(Calculators, self).__init__(**kwargs)
        self.params = [self.cf_M, self.cf_R, self.cf_T, self.cf_v_esc, self.cf_v_orb]
        self.G,self.M,self.R,self.T,self.v_orb,self.v_esc = sympy.symbols('G M R T v_orb v_esc')

        self.symbolmap = {self.cf_M:self.M, self.cf_R:self.R, self.cf_T:self.T,
            self.cf_v_orb:self.v_orb, self.cf_v_esc:self.v_esc}
        self.symbolmap2 = {self.M:self.cf_M, self.R:self.cf_R, self.T:self.cf_T,
            self.v_orb:self.cf_v_orb, self.v_esc:self.cf_v_esc}

        self.eqn_TR = self.T**2 - (4*sympy.pi**2)/(self.G * self.M) * self.R**3
        self.eqn_vo = self.v_orb - sympy.sqrt((self.G * self.M) / self.R)
        self.eqn_ve = self.v_esc - sympy.sqrt((2*self.G * self.M) / self.R)

    def valueupdate(self, cf=None, text=None):
        if any([p is None for p in self.params]):
            self.params = [self.cf_M, self.cf_R, self.cf_T, self.cf_v_orb, self.cf_v_esc]
            self.symbolmap = {self.cf_M:self.M, self.cf_R:self.R, self.cf_T:self.T,
                              self.cf_v_orb:self.v_orb, self.cf_v_esc:self.v_esc}
            self.symbolmap2 = {self.M:self.cf_M, self.R:self.cf_R, self.T:self.cf_T,
                               self.v_orb:self.cf_v_orb, self.v_esc:self.cf_v_esc}
            return
        for p in self.params:
            if p.get() is None or p.get() <= 0:
                p.valid = False
            else :
                p.valid = True
        if not cf.valid:
            return
        knowns = {self.G: self.cf_G.get(), self.symbolmap[cf]:cf.get()}
        for p in self.params:
            if p.valid and not (self.symbolmap[p] in knowns):
                knowns[self.symbolmap[p]] = p.get()
                break
        else :
            return
        if self.v_orb in knowns and self.v_esc in knowns:
            return
        unknowns = [v for v in self.symbolmap.values() if v not in knowns]
        for p in self.params:
            p.ontext_callbacks = []
        self.evaluate(unknowns, knowns)
        for p in self.params: 
            p.ontext_callbacks = [self.valueupdate]

    def evaluate(self, to_find, knowns):
        try :
            unknowns = to_find[:]
            eq_TR = self.eqn_TR.subs(knowns)
            eq_vo = self.eqn_vo.subs(knowns)
            eq_ve = self.eqn_ve.subs(knowns)
            eqmap = {self.v_orb:eq_vo, self.v_esc:eq_ve, self.T:eq_TR}
            if self.M in unknowns and self.R in unknowns:
                if self.v_orb in knowns:
                    aa = sympy.solve([eq_TR, eq_vo], [self.M,self.R])
                else :
                    aa = sympy.solve([eq_TR, eq_ve], [self.M,self.R])
                unknowns.pop(unknowns.index(self.M))
                unknowns.pop(unknowns.index(self.R))
                knowns[self.M] = math.fabs(aa[0][0])
                knowns[self.R] = math.fabs(aa[0][1])
            elif self.M in unknowns and self.R in knowns:
                for v in knowns:
                    if v in eqmap:
                        m = sympy.solve(eqmap[v], self.M)
                        break
                unknowns.pop(unknowns.index(self.M))
                knowns[self.M] = math.fabs(m[0])
            elif self.R in unknowns and self.M in knowns:
                for v in knowns:
                    if v in eqmap:
                        r = sympy.solve(eqmap[v], self.R)
                        break
                unknowns.pop(unknowns.index(self.R))
                knowns[self.R] = math.fabs(r[0])
            for u in unknowns :
                x = sympy.solve(eqmap[u].subs(knowns), u)
                knowns[u] = math.fabs(x[0])
            for x in knowns:
                if math.fabs(knowns[x] - round(knowns[x])) < 0.00000000000001:
                    knowns[x] = round(knowns[x])
            for q in to_find:
                self.symbolmap2[q].text = str(knowns[q])
                self.symbolmap2[q].cursor = (0,0)
        except Exception as err:
            Logger.error(f"Calculators : Error occurred while calculating values for \
                unknowns={to_find}, knowns={knowns}", exc_info=str(err))

    def clearinputs(self):
        for p in self.params:
            p.ontext_callbacks = []
            p.text = ""
            p.ontext_callbacks = [self.valueupdate]


class GravityAppUI(BoxLayout):

    tabpanel = ObjectProperty(None)
    acnview = ObjectProperty(None)
    createtab = ObjectProperty(None)
    simultab  = ObjectProperty(None)
    calctab = ObjectProperty(None)
    settingtab = ObjectProperty(None)
    createarea = ObjectProperty(None)
    templatebtn = ObjectProperty(None)
    simulator = ObjectProperty(None)
    calculators = ObjectProperty(None)
    
    tabpos = StringProperty('top_mid')

    def __init__(self, **kwargs):
        super(GravityAppUI, self).__init__(**kwargs)

        self.templatemodels = []
        self.tmplbtn_defaulttext = u"[font=fonts/Iconize-Italic][size=30] c [/size]\
[/font] Templates   "
        self.helpdialog = None
        self.infodialog = None
        Clock.schedule_once(lambda t : self.loadtemplate(None))
        Clock.schedule_once(lambda t : self.inithelpdialog())
        Clock.schedule_once(lambda t : self.initinfodialog())

    def addobj(self):
        self.createarea.add_widget(PlanetInput())

    def clearinputs(self):
        self.createarea.clear_widgets()
        self.createarea.add_widget(Label(size_hint_y=None, height='30dp',
            halign='left', font_size='14dp', color=[0.8,0.8,0.8,1], text="\
Add objects to be simulated and specify their initial coordinates and \
parameters here : "))
        self.createarea.add_widget(SettingSpacer())
        self.templatebtn.text = self.tmplbtn_defaulttext

    def _updateinputindices(self): #, wid, attrib):
        pl = self.createarea.children
        for x in pl :
            if isinstance(x, PlanetInput):
                x.index = len(pl) - pl.index(x) - 2

    def savetofile(self, fileobj):
        cnf = App.get_running_app().config
        data = self.processinput()
        if data is not None :
            try :
                d = {"settings":{
                    'G':float(cnf.get('sim', 'const_G')),
                    'dt':float(cnf.get('sim', 'const_dt')),
                    'bound':int(float(cnf.get('sim', 'bound'))),
                    'rand':int(cnf.get('sim', 'randomize')),
                    'polar':int(cnf.get('obj', 'polar')),
                    'collide':int(cnf.get('collision', 'allow_collide')),
                    'rf':float(cnf.get('collision', 'r_frac')),
                    'vf':float(cnf.get('collision', 'v_frac')),
                    'ix':int(float(cnf.get('anim', 'ini_x'))),
                    'iy':int(float(cnf.get('anim', 'ini_y'))),
                    'iz':float(cnf.get('anim', 'ini_z')),
                    'ir':float(cnf.get('anim', 'ini_r'))},
                     "data":data}
                json.dump(d, fileobj, indent=2)
                InfoDialog(title='Success', message="The model has been saved !")
            except Exception as err:
                Logger.error('Save : Failed to save data to file', exc_info=str(err))
                InfoDialog(title='Unknown Error', message="The data could not \
be saved properly. The output file may be incomplete.")
            finally:
                fileobj.close()

    def loadfile(self, fileobj):
        try :
            d = json.load(fileobj)
            s = d["settings"]
            QuestionDialog(title='Model Settings', question=f"""   The model being \
loaded has the following settings -
       Gravitational constant (G) : {s['G']}
       Time interval : {s['dt']}
       Boundary : {s['bound']}
       Randomize : {bool(s['rand'])}
       Polar Coordinates : {bool(s['polar'])}
       Enable collisions : {bool(s['collide'])}
       Collision Proximity : {s['rf']}
       Velocity Loss : {s['vf']}
       Initial X : {s['ix']}
       Initial Y : {s['iy']}
       Initial Zoom : {s['iz']}
       Initial Rotation: {s['ir']}\n
   Do you want to change the current app settings to these and proceed ?
   (The settings panel may still display the current values till \
the app is restarted.)""", size_hint=(0.7, 0.7),
                           action=lambda c: self._finishimport(s,c,d['data']))
        except Exception as err:
            Logger.error('Load File : Loading model data failed', exc_info=str(err))
            InfoDialog(title='Unknown Error', message="An error occurred while \
loading the model data from file")
        finally :
            fileobj.close()

    def _finishimport(self, setigs, confirm, data):
        self.loadfilesetg(setigs,confirm)
        self.loadfileui(data)

    def loadfileui(self, d):
        try :
            for obj in d :
                w = PlanetInput()
                w.setcolour(obj["colour"])
                w.mass.text = str(obj["mass"])
                w.radius.text = str(obj["radius"])
                w.trail.value = int(obj["trail"]) // w.t_scale
                x, y, vx, vy = obj['x'], obj['y'], obj['vx'], obj['vy']
                if App.get_running_app().config.getboolean('obj', 'polar'):
                    x, y = to_polar(x, y)
                    vx, vy = to_polar(vx, vy)
                w.pos0.text, w.pos1.text = str(x), str(y)
                w.vel0.text, w.vel1.text = str(vx), str(vy)
                self.createarea.add_widget(w)
        except Exception as err:
            Logger.error('Load UI : Filling imported data in UI failed', exc_info=str(err))
            InfoDialog(title='Unknown Error', message="An error occurred while \
loading the model data to the interface")

    def loadfilesetg(self, s, yesno):
        if yesno:
            cnf = App.get_running_app().config
            cnf.set('sim', 'const_G', s['G'])
            cnf.set('sim', 'const_dt', s['dt'])
            cnf.set('sim', 'bound', int(s['bound']))
            cnf.set('sim', 'randomize', int(s['rand']))
            cnf.set('obj', 'polar', int(s['polar']))
            cnf.set('collision', 'allow_collide', int(s['collide']))
            cnf.set('collision', 'r_frac', s['rf'])
            cnf.set('collision', 'v_frac', s['vf'])
            cnf.set('anim', 'ini_x', s['ix'])
            cnf.set('anim', 'ini_y', s['iy'])
            cnf.set('anim', 'ini_z', s['iz'])
            cnf.set('anim', 'ini_r', s['ir'])
            Logger.info('Import : Settings changed according to model')            
            

    def processinput(self):
        objects = []
        poss = {}
        for w in self.createarea.children :
            if isinstance(w, PlanetInput):
                p = dict()
                p['id'] = w.idlbl.text
                c = w.colour.background_color
                if len(c)!=4 or any([i<0 for i in c]) or any([i>1 for i in c]):
                    self._warn('colour', w)
                    return None
                p['colour'] = c
                try :
                    p['mass'] = float(w.mass.text)
                except ValueError :
                    self._warn('mass', w)
                    return None
                try :
                    p['radius'] = float(w.radius.text)
                except ValueError :
                    self._warn('radius', w)
                    return None
                try :
                    p['trail'] = int(w.t_scale * w.trail.value)
                except :
                    self._warn('trail length', w)
                    return None
                try :
                    if not w.pos0.text:
                        w.pos0.text = '0'
                    if not w.pos1.text:
                        w.pos1.text = '0'
                    x, y = float(w.pos0.text), float(w.pos1.text)
                    if App.get_running_app().config.getboolean('obj', 'polar'):
                        x, y = to_cartesian(x, y)
                    p['x'], p['y'] = x, y
                    if (x,y) in poss.keys():
                        InfoDialog(title='Error : Coinciding objects',
message=f"Objects {poss[(x,y)]} and {p['id']} were given approximately same \
initial positions - Please change any coordinate(s) so that they don't coincide.")
                        Logger.warning("Create Panel: Coinciding objects detected")
                        return None
                    else :
                        poss[(x,y)] = p['id']
                except ValueError :
                    self._warn('position', w)
                    return None
                try :
                    if not w.vel0.text:
                        w.vel0.text = '0'
                    if not w.vel1.text:
                        w.vel1.text = '0'
                    vx, vy = float(w.vel0.text), float(w.vel1.text)
                    if App.get_running_app().config.getint('obj', 'polar'):
                        vx, vy = to_cartesian(vx, vy)
                    p['vx'], p['vy'] = vx, vy
                except ValueError :
                    self._warn('velocity', w)
                    return None
                objects.append(p)
        return objects

    def _warn(self, param, wid):
        InfoDialog(title= 'Error : Invalid '+param+' in object {}'.format(
            wid.index), message="Check that all objects have a valid {} \
before continuing.\nAll numeric fields (mass, radius, position, velocity) cannot be\
 blank and can only contain digits 0-9, decimal point . , exponent e or initial + or - sign.\
 Choose a colour (RGBA) and trail length by adjusting the sliders.".format(param))
        Logger.warning("Create Panel: Error processing {} of input {} - {}".format(
            param, wid.index, repr(wid)))

    def convertinput(self, val):
        plr = bool(int(val))
        if any([isinstance(w, PlanetInput) for w in self.createarea.children]):
            now = 'polar' if plr else 'cartesian'
            then = 'cartesian' if plr else 'polar'
            InfoDialog(title='Warning', message='All objects that are currently\
 defined in the create tab are now using {} coordinates. Their position & \
velocity values have been converted from the old {} ones wherever possible.'.format(now,then)) 
        for w in self.createarea.children :
            if isinstance(w, PlanetInput):
                w.usepolar = plr
                try :
                    p0, p1 = float(w.pos0.text), float(w.pos1.text)
                    if plr : p2, p3 = to_polar(p0, p1)
                    else : p2, p3 = to_cartesian(p0, p1)
                    w.pos0.text, w.pos1.text = str(p2), str(p3)
                except :
                    pass
                try :
                    v0, v1 = float(w.vel0.text), float(w.vel1.text)
                    if plr : v2, v3 = to_polar(v0, v1)
                    else : v2, v3 = to_cartesian(v0, v1)
                    w.vel0.text, w.vel1.text = str(v2), str(v3)
                except :
                    pass

    def loadtemplate(self, text):
        if text is None:
            with open('templates/templates.json', 'r', encoding='utf-8') as tf :
                self.templatemodels = json.load(tf)
            Logger.info('Templates : Reloaded model list')
            self.templatebtn.values = [m['name'] for m in self.templatemodels]
        elif text == self.tmplbtn_defaulttext :
            return
        else :
            for model in self.templatemodels:
                if model['name']==text:
                    if os.path.isfile(model['path']):
                        self.loadfile(open(model['path'], 'r', encoding='utf-8'))
                        break
            else:
                Logger.warning(f'Templates : Could not find or open model {text}')
                InfoDialog(title="Template Missing", 
                    message="The selected model could not be located !")

    def run(self):
        cnf = App.get_running_app().config
        gs = GravSystem(const_G = cnf.getfloat('sim', 'const_G'),
                        const_dt = cnf.getfloat('sim', 'const_dt'),
                        bound=cnf.getint('sim', 'bound'),
                        f_calc=cnf.getint('sim', 'f_calc'),
                        random=cnf.getboolean('sim', 'randomize'),
                        autoradius=cnf.getboolean('obj', 'autoradius'),
                        r_const=cnf.getfloat('obj', 'r_const'),
                        collision=cnf.getboolean('collision', 'allow_collide'),
                        rf=cnf.getfloat('collision', 'r_frac'),
                        vf=cnf.getfloat('collision', 'v_frac'),
                        tpdist = cnf.getfloat('anim', 'tpdist'))
        planets = self.processinput()
        if planets is not None :
            self.simulator.stop()
            for p in planets :
                PlanetObject(system=gs, m=p['mass'], x=p['x'], y=p['y'],
                             vx=p['vx'], vy=p['vy'], color=p['colour'],
                             radius=p['radius'], trail=p['trail'], idx=p['id'],
                             polar=cnf.getboolean('obj', 'polar'))
            self.simulator.begin(gs)
            self.tabpanel.switch_to(self.simultab)

    def inithelpdialog(self):
        with open('help.json', 'r', encoding='utf-8') as infofile:
            widgets = json.load(infofile)
        self.helpdialog = ContentDialog(widgets, show=False, spacing='15dp',
            title="How to use this App", size_hint=(0.8,0.8))

    def initinfodialog(self):
        self.infodialog = ContentDialog([
            {"class":"Image", "source":"icons/Solar-system.png"},
            {"class":"Label", "font_size":"20sp", "bold":True, "italic":True,
             "text":"Gravity"},
            {"class":"Label", "font_size":"16sp", "italic":True,
             "text":"Version 2.0\n"},
            {"class":"Label", 'color':(0.8,0.8,0.8,1), "halign":'center',
             "text":"Author - Gautam D\nMay-June 2020\n\n"+\
                    "Written in Python 3.8 using Kivy 1.11"}
        ], spacing='10dp', title="About", size_hint=(0.6,0.6), show=False)
                

class GravityApp(App):

    def __init__(self, **kwargs):
        super(GravityApp, self).__init__(**kwargs)

    def build(self):
        self.icon = "icons/Solar-system.png"
        Window.size = (1000, 750)
        root = GravityAppUI()
        self.settings_cls = GravSettings
        Logger.info(f"Gravity App : Starting... {str(datetime.now())}")
        return root

    def build_config(self, config): ############################
        config.setdefaults('sim', {
            'const_G': 5, 'const_dt': 0.01, 'f_calc':50, 
            'bound': 10000, 'randomize':int(False)})
        config.setdefaults('obj', {
            'polar': int(False), 'autoradius':int(True), 'r_const': 3})
        config.setdefaults('collision', {
            'allow_collide': int(True), 'r_frac': 0.8, 'v_frac':1.0})
        config.setdefaults('anim', {
            'f_draw': 50, 'bgcolor':[0,0,0,1], 'tpdist':1.0,
            'ax_visible':int(False), 'ini_x':0, 'ini_y':0, 'ini_z':100.0,
            'ini_r':0, 'move_step':10, 'zoom_step':5, 'turn_step':5})
        config.setdefaults('app', {
            'tabpos':'top', 'rootpath':'', 'autosc':int(False),
            'scpath':os.getcwd(), 'fullsc':0})

    def on_config_change(self, config, sec, key, val):
        maxzoom = 10000
        maxG = 1000
        maxfc = 200
        maxfd = Config.getint('graphics', 'maxfps')
        maxdist = 100000
        maxstep = 10000
        maxzstp = 100
        if config is self.config:
            token = (sec, key)
            Logger.info("Setting: Changing setting {} to {}".format(token, val))
            if token == ('sim', 'const_G'):
                if abs(float(val)) > maxG or abs(float(val)) <= 0:
                    self.correctsetting(config, sec, key, 5, msg=f'The value of G must lie between 0 and {maxG}, 0 excluded')
                self.root.calculators.cf_G.text = str(config.get('sim', 'const_G'))
            if token == ('sim', 'const_dt') :
                if float(val) < 0:
                    self.correctsetting(config, sec, key, 0.01, msg='The value of dt cannot be negative.')
            if token == ('sim', 'f_calc'):
                if float(val) < 0 or float(val) > maxfc:
                    self.correctsetting(config, sec, key, 50, msg=f'The calculation frequency must be between 0 and {maxfc}.')
            if token == ('obj', 'polar'):
                self.root.convertinput(val)
            if token == ('obj', 'autoradius'):
                for w in self.root.createarea.children :
                    if isinstance(w, PlanetInput):
                        w.autoradius = bool(int(val))
            if token == ('obj', 'r_const'):
                if float(val) <= 0:
                    self.correctsetting(config, sec, key, 3, msg='The value of density constant must be greater than zero.')
            if token == ('collision', 'r_frac'):
                if float(val) < 0 or float(val) > 1:
                    self.correctsetting(config, sec, key, 0.8, msg='The value of proximity must be between 0 and 1.')
            if token == ('collision', 'v_frac'):
                if float(val) < 0 or float(val) > 1:
                    self.correctsetting(config, sec, key, 1.0, msg='The value of velocity loss must be between 0 and 1.')
            if token == ('anim', 'f_draw'):
                if float(val) <= 0 or float(val) > maxfd:
                    self.correctsetting(config, sec, key, min(50, maxfd), msg=f'The redrawing framerate must be between 0 and {maxfd} (both excluded)')
            if token == ('anim', 'tpdist'):
                if float(val) < 0 :
                    self.correctsetting(config, sec, key, 1.0, msg='The value of point distance cannot be negative.')
            if token == ('sim', 'bound') or token == ('anim', 'ini_x') or token == ('anim', 'ini_y') :
                if abs(int(val)) > maxdist:
                    nam = {'bound':"the Boundary limit", 'ini_x':"initial X coordinate", 'ini_y':"initial Y coordinate"}[key]
                    self.correctsetting(config, sec, key, 10000, msg='The absolute value of {nam} must be less than {maxdist}')
            if token == ('anim', 'ini_z'):
                if float(val) <= 0 or float(val) >= maxzoom :
                    self.correctsetting(config, sec, key, 1.0, msg=f'The inital zoom must be between 0% and {maxzoom}% (both excluded).')
            if token == ('anim', 'move_step') or token == ('anim', 'turn_step'):
                if abs(float(val)) > maxstep :
                    self.correctsetting(config, sec, key, 10, msg=f'The absolute value of step size must be less than {maxstep}.')
            if token == ('anim', 'zoom_step'):
                if abs(float(val)) > maxzstp :
                    self.correctsetting(config, sec, key, 5, msg=f'The absolute value of step size must be less than {maxzstp}.')
            if token == ('app', 'tabpos'):
                self.root.tabpanel.tab_pos = val + '_mid'
            if token == ('app', 'rootpath'):
                if not os.path.isdir(val):
                    self.correctsetting(config, sec, key, '', msg='"{}" is not a valid directory.'.format(val))
            if token == ('app', 'scpath'):
                if not os.path.isdir(val):
                    self.correctsetting(config, sec, key, os.getcwd(), msg='"{}" is not a valid directory.'.format(val))
            

    def correctsetting(self, config, sec, key, val, msg='', prompt=True):
        config.set(sec, key, val)
        config.write()
        v = val if val != '' else '""'
        InfoDialog(title='Error', message = msg+'\nThe app will use the value {} instead till this is changed'.format(v))
        '''# Forcibly reconstruct the settings panel to show the change
        self._app_settings = GravSettings()
        self.build_settings(self._app_settings)
        if self.use_kivy_settings :
            self._app_settings.add_kivy_panel()
        self.open_settings()'''
        Logger.info("Setting: Changing setting ({}, {}) to {}".format(sec, key, val))

    def build_settings(self, settings):
        self.settings = settings
        self.use_kivy_settings = False
        with open(r"settings_tech.json", 'r', encoding='utf-8') as setg1file:
            setting1_jsdata = setg1file.read()
        with open(r"settings_anim.json", 'r', encoding='utf-8') as setg2file:
            setting2_jsdata = setg2file.read()
        settings.add_json_panel('Technical', self.config,
                                data=setting1_jsdata)
        settings.add_json_panel('Graphics & App', self.config,
                                data=setting2_jsdata)

    def display_settings(self, settings):
        if not settings in self.root.settingtab.children :
            self.root.settingtab.add_widget(settings)
        self.root.tabpanel.switch_to(self.root.settingtab)
        return True

    def close_settings(self, *args):
        if self.root.simulator.active :
            self.root.tabpanel.switch_to(self.root.simultab)
        else:
            self.root.tabpanel.switch_to(self.root.createtab)
        return True

    def on_pause(self):
        Logger.warning(f"Gravity App : Paused {str(datetime.now())}")

    def on_resume(self):
        Logger.warning(f"Gravity App : Resumed {str(datetime.now())}")


if __name__ == '__main__' :
    os.chdir(os.path.split(os.path.abspath(__file__))[0])
    _ = GravityApp()
    try :
        _.run()
    except Exception as _err :
        Logger.error("Gravity App : Uncaught error ", exc_info=str(_err))
