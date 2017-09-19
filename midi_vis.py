import mido
import pygame
import pygame.gfxdraw
import math
import threading
import time

### FOR DIFFERENT MIDIFILE CHANGE FILENAME AT LINE 201 ###

# Get tempo from Mido midi-file
def getTempo(midi_file):

	tempo = 0
	for msg in midi_file:
		if msg.type=="set_tempo":
			tempo = msg.tempo
			break
	return tempo

# Convert note(0-127) to point coordinates on a circle(45° - 315°)
def circle_p(note, radius, mn, mx):

	angle = 135 -(((127-note)-(127-mn))/(mx-mn))*270
	x = radius * math.cos(-angle*math.pi/180)
	y = radius * math.sin(-angle*math.pi/180)
	re = (round(x), round(y))
	return re

# Convert all midi-messages to a list of points [note, 0, time note_on, time note_off]
# The first two elements [note, 0, ..] are given to "set_coords" later, to convert them to circle coordinates.
def convert_2_points(midi_file):

	re = list()
	note_ons = list()
	pos = 0
	tempo = 0
	mx =0
	mn =127	
	for msg in midi_file:
		if msg.type=="set_tempo":			
			tempo = msg.tempo
			#print(tempo)
		if msg.type=="note_off" or (msg.type=="note_on" and msg.velocity==0):
			msg_s = msg.time
			pos += msg_s
			end_Point = [msg.note, 0, pos, 0]
			for el in note_ons:
				if el[0]==msg.note:
					#[note x, note y, pos-on, pos_off]
					new_Point = [msg.note, 0, el[2], pos]
					re.append(new_Point)
					note_ons.remove(el)			
			
		elif msg.type=="note_on" and msg.velocity>0:
			msg_s = msg.time
			pos += msg_s
			start_Point = [msg.note, 0, pos, 1]			
			note_ons.append(start_Point)
			if msg.note>mx:
				mx=msg.note
			if msg.note<mn:
				mn=msg.note
		else:			
			msg_s = msg.time
			pos += msg_s
	
	return re, tempo, mn, mx

# Convert first two elements of the point-list to circle coordinates
def set_coords(msg_l, radius, mn, mx):
	for point in msg_l:
		coords = circle_p(point[0], radius, mn, mx)
		point[0] = coords[0]
		point[1] = coords[1]

# Create a list of circles to draw the inner moving circles. 1 circle every 5 seconds.
def spawn_circles(l):
	re = list()
	c = 0
	while(c < l):
		re.append(c)
		c += 5
	re.append(c)
	return re

# Playsthe midi-file. Sets the global variables "global_t" (current time in seconds) and "midi_start" (True).
# This is probably not clean concurrent programming, but it works just fine so I kept it.
def play_midi(mid, stop_event):
	global global_t
	global midi_start
	
	for msg in mid:
		if not midi_start:
			midi_start = True
			global_t = 0
		wait_t = msg.time
		time.sleep(wait_t)
		if not msg.is_meta:
			port.send(msg)
		global_t += msg.time
		if stop_event.is_set():
			break

# Draws everything
def draw_screen(screen, width, height, radius, old_midi_t, new_midi_t, cur_t, msg_l, circles):

	# start execution time
	start_t = time.time()

	# check for "new_midi" (global_t) changed by the midi-playback. If true, take average time diff.
	if not midi_start:
		current_t = 0		
	elif old_midi_t!= new_midi_t:
		current_t = (cur_t + new_midi_t)/2
		old_midi_t = new_midi_t
	else:
		current_t = cur_t

	screen.fill((0,0,0))
	center_x = round(width/2)
	center_y = round(height/2)
	d = 100
	scale = 35
	
	# draw the center circle
	def draw_circle():	
		pygame.gfxdraw.aacircle(screen,  center_x, center_y, radius+4, (0,0,255))
		

	# draw the moving inner circles according to time-step (current_t)
	def draw_inner_circles():
		for c in circles:
			z = d + c*scale - current_t*scale
			col = max(0, min(155/(z/(d+100)), 155))
			if(z>1):
				pygame.gfxdraw.aacircle(screen,  center_x, center_y, round(radius/(z/d)), (0,0,col))

	# draw the note-played effect
	def draw_effect(x,y):		
		
		pygame.gfxdraw.aacircle(screen, x+center_x , y+center_y, 10, (55,50,10))
		pygame.draw.circle(screen, (200,190,10), (x+center_x , y+center_y), 3, 0)
		pygame.draw.circle(screen, (225,200,10), (x+center_x , y+center_y), 1, 0)


	# draw the red moving notes according to time-step (current_t)
	def draw_notes():
		for point in msg_l:
			
			x = point[0]
			y = point[1]
			z1 = (d + point[2]*scale) - current_t*scale
			z2 = (d + point[3]*scale) - current_t*scale
			x_p = round(x/(z1/d)) + center_x
			y_p = round(y/(z1/d)) + center_y
			p_width1 = max(1, min(round(4./(z1/d)), 6))
			p_width2 = max(1, min(round(4./(z2/d)), 6))
			col = max(0, min(255/(z1/(d+100)), 255))			
			x_p_end = round(x/(z2/d)) + center_x
			y_p_end = round(y/(z2/d)) + center_y

			if (round(z2) < d) and z1 >=1:
				
				pygame.draw.circle(screen, (60,0, 0), (x_p_end,y_p_end), p_width2, 1)				
				pygame.draw.line(screen,(60,0,0), (x_p,y_p), (x_p_end, y_p_end), 1)
				pygame.draw.circle(screen, (60,0,0), (x_p,y_p), p_width1, 0)	
				
			elif round(z1)<=d<=round(z2):
				#print("view", current_t, "time", point[2])
				pygame.gfxdraw.aacircle(screen,  center_x, center_y, radius+5, (0,0,120))
				pygame.draw.circle(screen, (255,100, 0), (x_p_end,y_p_end), p_width2, 1)
				#print((x_p,y_p))
				if z1<1:
					pygame.draw.line(screen,(255,100,0), (x/0.2+ center_x,y/0.2+ center_y), (x_p_end, y_p_end), 2)				
				else:
					pygame.draw.line(screen,(255,100,0), (x_p,y_p), (x_p_end, y_p_end), 2)

				if z1>=1:
					pygame.draw.circle(screen, (col,100,0), (x_p,y_p), p_width1, 0)
				draw_effect(x,y)

			elif z1>=1:
				
				pygame.draw.circle(screen, (col,0, 0), (x_p_end,y_p_end), p_width2, 1)
				pygame.draw.line(screen,(col,0,0), (x_p,y_p), (x_p_end, y_p_end), 1)
				pygame.draw.circle(screen, (col,0,0), (x_p,y_p), p_width1, 0)

	draw_inner_circles()
	draw_circle()
	draw_notes()
	pygame.display.update()

	# return exec-time and the latest midi time-stamp
	return (current_t+(time.time()-start_t)), old_midi_t
	



# read and prepare midi-file. CHANGE FILENAME HERE.
port = mido.open_output()
mid = mido.MidiFile('liz_et_trans4.mid')
# add a start delay to put all notes further back
tempo = getTempo(mid)
for trks in mid.tracks:
	trks.insert(0,mido.Message(type="note_off", velocity = 0, time=round(mido.second2tick(20,mid.ticks_per_beat,tempo))))
	trks.insert(0,mido.MetaMessage(type="set_tempo",tempo=tempo))
mid.save("preprocessed.mid")
pp = mido.MidiFile('preprocessed.mid')
# convert to point list
msg_l, tempo2, mn, mx = convert_2_points(pp)

# init pygame screen
pygame.init()
width = 640
height = 480
radius = round((height-200)/2)
screen = pygame.display.set_mode((width,height), pygame.HWSURFACE)
pygame.display.set_caption("MIDI Visualizer")
set_coords(msg_l, radius, mn, mx)
circles = spawn_circles(pp.length)

midi_start = False
global_t = 0
draw_t, old_t = draw_screen(screen, width, height, radius, -1 , global_t, 0, msg_l, circles)

# play midi-file in a concurrent thread
t1_stop = threading.Event()
t1 = threading.Thread(target=play_midi, args=[pp, t1_stop])
t1.start()
# main visualisation loop
gameExit = False
while not gameExit:
	for event in pygame.event.get():
		if event.type == pygame.QUIT:
			gameExit = True

	draw_t, old_t = draw_screen(screen, width, height, radius, old_t, global_t, draw_t, msg_l, circles)
	
	
	
t1_stop.set()
pygame.quit()

