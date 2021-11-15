# midijoy.py v0.6.9
# by thiccboy808/kerochan
# a midi to xinput interface
# to allow midi events to be
# used as controller input
# requires vjoy input emulator

# ~ Output types
#  ~ buttons
#  ~ axis
#  ~ dirpad (dont forget to actually implement into MiditoXInput)

# ~ Input types
#  ~ note on/off
#  ~ control change (axis)
#  ~ program change 
#  ~ pitch change (axis)

from ctypes import Structure
import os
os.environ[ 'PYGAME_HIDE_SUPPORT_PROMPT' ] = "hide"
import sys
import pyvjoy
import pygame
import pygame.midi
import pygame.compat
from pygame.locals import *
import pygame_gui
from enum import Enum

# constants!!!
VERSION = "0.6.9" # funi numbrszzz
ACTIVE_WIN_WIDTH = 710
ACTIVE_WIN_HEIGHT = 280
ACTIVE_WIN_SIZE = ( ACTIVE_WIN_WIDTH, ACTIVE_WIN_HEIGHT )
LIGHT_GRAY = ( 190, 190, 190 )
DARK_GRAY = ( 40, 40, 40 )

def addtuple( tup1, tup2 ):
  return tuple( map( lambda i, j: i + j, tup1, tup2 ) )

def print_devices():
  for i in range( pygame.midi.get_count() ):
    #info = 
    ( interf, name, input, output, opened ) = pygame.midi.get_device_info( i )
    if input: input = "(input)" 
    else: input = ""
    if output: output = "(output)" 
    else: output = ""
    if opened: opened = "open"
    else: opened = "closed"
    print( "%s: %s, %s %s%s: %s" % ( hex( i ), interf, name, input, output, opened ) )

# map types to state how to convert into xinput
class MapType( Enum ):
  SETBUTTON = 1
  SETAXIS = 2
  SETHAT = 4 # not implemented yet

class DataType( Enum ):
  NOTE = 1
  CTRL = 2
  PROG = 4
  PITCH = 8

# map is mapping settings for mapping events from midi to xinput
# input is midi input from pygame
# output is vjoy xinput device
class MidiToXInput:
  def __init__( self, iomap, input, output, printen ):
    self.input = input
    self.output = output
    self.printen = printen
    self.updatemap( iomap )
    self.paused = False
    self.iomap = iomap

  def handleevent( self, e ):
    if e.type in [ pygame.midi.MIDIIN ]:
      if not self.paused:
        status =  e.status >> 4
        if status == 8:
          self.noteoff( e )
        elif status == 9:
          self.noteon( e )
        elif status == 11:
          self.controlchange( e )
        elif status == 12:
          self.programchange( e )
        elif status == 14:
          self.pitchwheel( e )
        if self.printen:
          print( "status:%s data:%s %s %s time:%s id:%s" % ( hex( e.status ), hex( e.data1 ), hex( e.data2 ), 
          hex( e.data3 ), hex( e.timestamp ), hex( e.vice_id ) ) )

  def setmaplink( self, data, datatype, mapdata, maptype ):
    for i in range( len( self.iomap ) ):
      if ( self.iomap[ i ][ 0 ] == data ) and ( self.iomap[ i ][ 1 ] == datatype ):
        self.iomap[ i ] = ( data, datatype, mapdata, maptype )
        if self.printen:
          print( "replaced mapping: " + str( self.iomap[ i ] ) )
        return
    self.iomap.append( ( data, datatype, mapdata, maptype ) )
    if self.printen:
      print( "added mapping: " + str( self.iomap[ i ] ) )
    return

  def updatemap( self, iomap ):
    self.iomap = iomap
    return

  # this will break (at least spam) if used for a control or pitch
  def setbutton( self, e, buttonid, set ):
    if buttonid < 1:
      if self.printen:
        print( "button %s isnt a button" % hex( buttonid ) )
      return 0
    self.output.set_button( buttonid, set )
    return buttonid

  def setaxis( self, e, flip, isx, isy = False ):
    value = e.data2 << 8
    if flip:
      value = 0x8000 - value
    if isx:
      self.output.set_axis( pyvjoy.HID_USAGE_X, value )
    if isy:
      self.output.set_axis( pyvjoy.HID_USAGE_Y, value )

  # def sethat( self, e, ): set directional pad/hat button mapping

  # maps and executes to xinput
  def mapto( self, e, datatype, set = False ):
    for i in range( len( self.iomap ) ):
      if self.iomap[ i ][ 0 ] == e.data1 and datatype == self.iomap[ i ][ 1 ]:
        maptype = self.iomap[ i ][ 3 ]
        if maptype == MapType.SETBUTTON:
          self.setbutton( e, self.iomap[ i ][ 2 ], set )
        elif maptype == MapType.SETAXIS:
          flip = ( self.iomap[ i ][ 2 ] >> 2 )
          isx = ( self.iomap[ i ][ 2 ] >> 1 ) & 1
          isy = self.iomap[ i ][ 2 ] & 1
          self.setaxis( e, flip, isx, isy )
  # todo: handle map struct to map to various funtions
  def noteoff( self, e ):
    if self.printen:
      print( "note off event:" )
    self.mapto( e, DataType.NOTE, False )
    #self.setbutton( e,   )

  def noteon( self, e ):
    if self.printen:
      print( "note on event:" )
    self.mapto( e, DataType.NOTE, True )

  def programchange( self, e ):
    if self.printen:
      print( "program change event:" )
    self.mapto( e, DataType.PROG )
    #self.setbutton( e, False )

  def controlchange( self, e ):
    if self.printen:
      print( "control change event:" )
    self.mapto( e, DataType.CTRL )
    #self.setaxis( e, True, False, True )

  def pitchwheel( self, e ):
    if self.printen:
      print( "pitch wheel event:" )
    self.mapto( e, DataType.PITCH )
    #self.setaxis( e, False, True, False )

  def pause( self ):
    self.paused = True
  
  def resume( self ):
    self.paused = False

# TODO: Actually make buttons for control and pitch input mapping
# TODO: and program change mapping buttons too (maybe) lmao
# todo: make layers of gui dissapear
class MidiJoyGUI:
  def __init__( self, mapper ):
    self.mapper = mapper
    self.manager = pygame_gui.UIManager( ACTIVE_WIN_SIZE, "themes/theme.json" )
    self.background = pygame.Surface( ACTIVE_WIN_SIZE )
    self.background.fill( self.manager.ui_theme.get_colour( "dark_bg" ) )
    #self.maincontainer = pygame_gui.c
    self.newnotes()
    self.newassigner()
    self.newoctavechanger()
    self.clock = pygame.time.Clock()

  def setnotebutton( self ):
    change = False
    for note in self.selectednotes:
      num = self.notes.index( note )
      if note.text == self.noteassign:
        note.set_text( self.buttonassigner.text )
        change = True
        #self.mapper.updatemap( iomap )
        maptype = MapType.SETBUTTON
        if not hasattr( self, "buttonassigner" ):
          maptype = MapType.SETAXIS
        # !!! incorrenct input button number will fuck everything up cause letters cant be digits (FIX ITTT) !!!
        if self.buttonassigneroption.isdigit():
          mapopt = int( self.buttonassigneroption )
        # !!! add alert that its invalid input (without it breaking shit)
        self.mapper.setmaplink( self.notemidioffset + num, DataType.NOTE, mapopt, maptype )
    if change:
      self.selectednotes = []

  def setnoteaxis( self ):
    change = False
    for note in self.selectednotes:
      mapopt = 0
      if self.axisassigneroption == "X":
        mapopt = 0b10
      elif self.axisassigneroption == "Y":
        mapopt = 0b01
      if self.axisassigneroption == "-X":
        mapopt = 0b110
      elif self.axisassigneroption == "-Y":
        mapopt = 0b101
      if mapopt != 0:
        change = True
        num = self.notes.index( note )
        note.set_text( self.axisassigneroption )
        self.mapper.setmaplink( self.notemidioffset + num, DataType.NOTE, mapopt, MapType.SETAXIS )
    if change:
      self.selectednotes = []

  def handleevent( self, e, iomap ):
    self.manager.process_events( e )
    if e.type == pygame.USEREVENT:
      if e.user_type == pygame_gui.UI_TEXT_ENTRY_CHANGED:
        if hasattr( self, "buttonassigner" ):
          self.buttonassigneroption = e.text
      if e.user_type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
        # button assigner
        if hasattr( self, "buttonassigner" ):
          self.buttonassigneroption = e.text
          self.setnotebutton()
      if e.user_type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
        # assigner
        if e.text == "Button":
          if hasattr( self, "axisassigner" ):
            self.axisassigner.kill()
            del self.axisassigner
          self.newbuttonassign()
          return
        elif e.text == "Axis":
          if hasattr( self, "buttonassigner" ):
            self.buttonassigner.kill()
            del self.buttonassigner
          self.newaxisassign()
        # axis assiner
        elif e.text == "X" or e.text == "Y" or e.text == "-X" or e.text == "-Y":
          if hasattr( self, "axisassigner" ):
            self.axisassigneroption = e.text
            self.setnoteaxis()
      if e.user_type == pygame_gui.UI_BUTTON_PRESSED:
        if e.ui_element == self.confirmassign:
          if hasattr( self, "buttonassigner" ):
            self.setnotebutton()
          if hasattr( self, "axisassigner" ):
            self.setnoteaxis()
        elif e.ui_element == self.octaveup:
          self.notemidioffset += 12
          # !!! UPDATE BUTTONS TO THE NEW RANGE HERE !!!
        for note in self.notes:
          if e.ui_element == note:
            self.selectednotes.append( e.ui_element )
            note.set_text( self.noteassign )
  
  def update( self, display ):
    self.manager.update( self.clock.tick( 60 ) / 1000.0 )
    display.blit( self.background, ( 0, 0 ) )
    self.manager.draw_ui( display )

  def newnotes( self ):
    # todo: implement octave buttons for notes to cover the whole midi note range
    self.noteassign = "..."
    self.notesposition = ( 10, 10 )
    self.notessize = ( 40, 80 )
    self.selectednotes = []
    self.notemidioffset = 48
    self.notes = [ pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 0, 80 ) ), self.notessize ), text = "1", manager = self.manager ), 
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 25, 0 ) ), self.notessize ), text = "2", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 50, 80 ) ), self.notessize ), text = "3", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 75, 0 ) ), self.notessize ), text = "4", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 100, 80 ) ), self.notessize ), text = "5", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 150, 80 ) ), self.notessize ), text = "6", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 175, 0 ) ), self.notessize ), text = "7", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 200, 80 ) ), self.notessize ), text = "8", manager = self.manager ), 
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 225, 0 ) ), self.notessize ), text = "9", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 250, 80 ) ), self.notessize ), text = "10", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 275, 0 ) ), self.notessize ), text = "11", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 300, 80 ) ), self.notessize ), text = "12", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 350, 80 ) ), self.notessize ), text = "13", manager = self.manager ), 
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 375, 0 ) ), self.notessize ), text = "14", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 400, 80 ) ), self.notessize ), text = "15", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 425, 0 ) ), self.notessize ), text = "16", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 450, 80 ) ), self.notessize ), text = "17", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 500, 80 ) ), self.notessize ), text = "18", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 525, 0 ) ), self.notessize ), text = "19", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 550, 80 ) ), self.notessize ), text = "20", manager = self.manager ), 
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 575, 0 ) ), self.notessize ), text = "21", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 600, 80 ) ), self.notessize ), text = "22", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 625, 0 ) ), self.notessize ), text = "23", manager = self.manager ),
      pygame_gui.elements.UIButton( 
      relative_rect = pygame.Rect( addtuple( self.notesposition, ( 650, 80 ) ), self.notessize ), text = "24", manager = self.manager ) ]

  def newoctavechanger( self ):
    self.octavedown = pygame_gui.elements.UIButton( 
      pygame.Rect( addtuple( self.notesposition, ( 0, 230 ) ), ( 100, 30 ) ), text = "⇦", manager = self.manager )
    self.octaveup = pygame_gui.elements.UIButton( 
      pygame.Rect( addtuple( self.notesposition, ( 100, 230 ) ), ( 100, 30 ) ), text = "⇨", manager = self.manager )

  def newassigner( self ):
    if not hasattr( self, "typeassigner" ):
      self.confirmassign = pygame_gui.elements.UIButton( 
      pygame.Rect( addtuple( self.notesposition, ( 100, 200 ) ), ( 100, 30 ) ), text = "Assign", manager = self.manager )
      self.typeassigner = pygame_gui.elements.UIDropDownMenu( [ "Button", "Axis", "Directional" ], "Choose Output...",
      pygame.Rect( addtuple( self.notesposition, ( 0, 170 ) ), ( 200, 30 ) ), manager = self.manager )

  def newbuttonassign( self ):
    if not hasattr( self, "buttonassigner" ):
      self.buttonassigner = pygame_gui.elements.UITextEntryLine( 
        pygame.Rect( addtuple( self.notesposition, ( 25, 200 ) ), ( 50, 30 ) ), manager = self.manager )

  def newaxisassign( self ):
    if not hasattr( self, "axisassigner" ):
      # CHANGE AXISASSIGNER TO A DROP DOWN MENU!!!!!!!!!! 
      self.axisassigneroption = "..."
      self.axisassigner = pygame_gui.elements.UIDropDownMenu( [ "X", "Y", "-X", "-Y" ], "...",
        pygame.Rect( addtuple( self.notesposition, ( 0, 200 ) ), ( 100, 30 ) ), manager = self.manager )

  # todo: add an enter/accept button that fills rest of "block" of assigner
  # todo: perferibly checks (and disables) if theres any selected buttons to change

def loop( input, output, printen ):
  # input to output map format:
  # ( data, datatype, map, maptype )
  # data format is depenent on datatype
  # and map value meaning depends on maptype as well
  iomap = [ ( 1, DataType.CTRL, 1, MapType.SETAXIS ), # default midi to xinput map
  ( 48, DataType.NOTE, 1, MapType.SETBUTTON ), ( 49, DataType.NOTE, 2, MapType.SETBUTTON ),
  ( 50, DataType.NOTE, 3, MapType.SETBUTTON ), ( 51, DataType.NOTE, 4, MapType.SETBUTTON ),
  ( 52, DataType.NOTE, 5, MapType.SETBUTTON ), ( 53, DataType.NOTE, 6, MapType.SETBUTTON ),
  ( 54, DataType.NOTE, 7, MapType.SETBUTTON ), ( 55, DataType.NOTE, 8, MapType.SETBUTTON ),
  ( 56, DataType.NOTE, 9, MapType.SETBUTTON ), ( 57, DataType.NOTE, 10, MapType.SETBUTTON ),
  ( 58, DataType.NOTE, 11, MapType.SETBUTTON ), ( 59, DataType.NOTE, 12, MapType.SETBUTTON ),
  ( 60, DataType.NOTE, 13, MapType.SETBUTTON ), ( 61, DataType.NOTE, 14, MapType.SETBUTTON ),
  ( 62, DataType.NOTE, 15, MapType.SETBUTTON ), ( 63, DataType.NOTE, 16, MapType.SETBUTTON ),
  ( 64, DataType.NOTE, 17, MapType.SETBUTTON ), ( 65, DataType.NOTE, 18, MapType.SETBUTTON ),
  ( 66, DataType.NOTE, 19, MapType.SETBUTTON ), ( 67, DataType.NOTE, 20, MapType.SETBUTTON ),
  ( 68, DataType.NOTE, 21, MapType.SETBUTTON ), ( 69, DataType.NOTE, 22, MapType.SETBUTTON ),
  ( 70, DataType.NOTE, 23, MapType.SETBUTTON ), ( 71, DataType.NOTE, 24, MapType.SETBUTTON ) ]
  mapper = MidiToXInput( iomap, input, output, printen )
  eventget = pygame.fastevent.get
  eventpost = pygame.fastevent.post 
  display = pygame.display.set_mode( ACTIVE_WIN_SIZE )
  font = pygame.font.Font( "fonts/Roboto-Medium.ttf", 32 )
  midijoygui = MidiJoyGUI( mapper )
  pygame.display.set_caption( "MidiJoy v" + VERSION )
  running = True
  while running:
    midijoygui.update( display )
    pygame.display.update()
    events = eventget()
    for e in events:
      if e.type in [ QUIT ]:
        running = False
      mapper.handleevent( e )
      midijoygui.handleevent( e, iomap )
    if input.poll():
      midievents = input.read( 10 )
      pygameevents = pygame.midi.midis2events( midievents, input.device_id )
      for pye in pygameevents:
        eventpost( pye )
  del input

# this shit is redundent as fuck, ur already doing some init in the loop function before the loop
def init( mididevid = None, joydevid = None, printen = False ):
  pygame.init()
  pygame.fastevent.init()
  pygame.midi.init()
  pygame.font.init()
  if printen:
    print_devices()
  if mididevid is None:
    mididevid = pygame.midi.get_default_input_id()
    if mididevid == -1:
      print( "error!!! no midi devices found..." )
      exit()
  if printen:
    print( "using:", hex( mididevid ) )
  if joydevid is None:
    joydevid = 1
  mididev = 0
  joydev = 0
  try:
    mididev = pygame.midi.Input( mididevid )
    joydev = pyvjoy.VJoyDevice( joydevid )
  except pyvjoy.exceptions.vJoyNotEnabledException:
    print( "error!!! vjoy couldn't be found/isnt enabled..." )
    exit()
  except:
    print( "error!!! unknown exception occured..." )
    exit()
  loop( mididev, joydev, printen )
  
def destroy():
  pygame.midi.quit()

print( "midijoy midi to joystick interface v" + VERSION )
input = None
output = None
printen = False
if "-h" in sys.argv or "--help" in sys.argv:
  print( "usage:" )
  print( "  python midijoy.py [options]" )
  print( "options:" )
  print( "  -h, --help: you already know what this does" )
  print( "  -i, --input: midi input device id" )
  print( "  -o, --output: joystick device id" )
  print( "  -v, --verbose: enable verbose mode" )
  exit()
if "-i" in sys.argv or "--input" in sys.argv:
  input = int( sys.argv[ sys.argv.index( "-i" ) + 1 ] )
if "-o" in sys.argv or "--output" in sys.argv:
  output = int( sys.argv[ sys.argv.index( "-o" ) + 1 ] )
if "-v" in sys.argv or "--verbose" in sys.argv:
  printen = True
init( input, output, printen )
destroy()
     
