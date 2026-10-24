extends Node2D

const BLUE := Color("3e69a0")
const WHITE := Color.WHITE
var local_time := 0.0
var shot_time := 0.0
var laser_age := -1.0
var phone_icon := PackedVector2Array()
var phone_frame := PackedVector2Array()
var phone_speaker := PackedVector2Array()
var phone_home := PackedVector2Array()
var icon_centre := Vector2.ZERO
var line_start := Vector2.ZERO
var heroine: Texture2D
var shadow: Texture2D
var heroine_origin := Vector2(18780,5)
var heroine_size := Vector2(1010,1280)
var cup_anchor := Vector2.ZERO

func unit(a: float,b: float,t: float) -> float:
	return clampf((t-a)/(b-a),0,1)

func travel_time(t: float) -> float:
	# Phase clock: arrival6.30 is actual song65.100 after the front compression.
	return t

func acceleration_out(q: float) -> float:
	var split := 0.74
	return pow(q,3)/pow(split,2) if q < split else 1-pow(1-q,3)/pow(1-split,2)

func flight(t: float) -> float:
	return acceleration_out(unit(5.17,6.30,t))

func point_at(q: float) -> Vector2:
	# The message travels above the connecting string, never threaded onto it.
	var depart := smoothstep(0,0.09,q)
	var height := lerpf(line_start.y-icon_centre.y,160,depart)
	return route_at(q)+Vector2((icon_centre.x-line_start.x)*(1-depart)-120*smoothstep(0.88,1,q),-height)

func route_at(q: float) -> Vector2:
	return line_start.lerp(cup_anchor,q)+Vector2(0,25*sin(q*PI))

func partial(points: PackedVector2Array,q: float,color: Color,width: float) -> void:
	if q <= 0 or points.size() < 2: return
	var total := 0.0
	for i in range(1,points.size()): total += points[i-1].distance_to(points[i])
	var remaining := total*clampf(q,0,1)
	var drawn := PackedVector2Array([points[0]])
	for i in range(1,points.size()):
		var length := points[i-1].distance_to(points[i])
		if remaining < length:
			drawn.append(points[i-1].lerp(points[i],remaining/maxf(length,0.0001)))
			break
		drawn.append(points[i])
		remaining -= length
	if drawn.size() >= 2: draw_polyline(drawn,color,width,true)

func update_at(t: float, actual_time: float) -> void:
	shot_time = t
	laser_age = actual_time-6.00
	local_time = travel_time(t)
	visible = t >= 4.95
	queue_redraw()

func packet(t: float,opacity: float) -> void:
	if t < 5.17 or phone_icon.size() < 7: return
	var q := flight(t)
	var centre := point_at(q)
	var dissolve := smoothstep(5.48,5.73,t)
	# Reception keeps drifting and expanding; no clamped end pose for the waves.
	var received_age := maxf(t-6.30,0)
	var drift := received_age-0.20*(1-exp(-received_age/0.20))
	centre += Vector2(25*drift,-8*drift)
	var fade := exp(-0.72*received_age)
	var colour := BLUE.lerp(WHITE,smoothstep(0.035,0.065,q))
	colour.a = opacity*fade
	var unroll := smoothstep(5.17,5.41,t)
	var angle := (phone_icon[1]-phone_icon[0]).angle()
	# Dissolve the letter into two quiet wave glints above the string.
	# Crossfade instead of interpolating crossed envelope edges into sine strands.
	var envelope_colour := colour
	envelope_colour.a *= 1-dissolve
	for strand in 6:
		var a := (phone_icon[strand]-icon_centre).rotated(-angle*unroll)*lerpf(1,1.5,unroll)
		var b := (phone_icon[strand+1]-icon_centre).rotated(-angle*unroll)*lerpf(1,1.5,unroll)
		if envelope_colour.a > 0.001:
			draw_line(centre+a,centre+b,envelope_colour,6,true)
	var wave_colour := colour
	wave_colour.a *= 0.22*dissolve
	for wave in 2:
		var radius := 70.0+wave*30.0+32*drift
		var arc_centre := centre+Vector2(-170+wave*70,0)
		if wave_colour.a > 0.001:
			draw_arc(arc_centre,radius,-PI/5,PI/5,25,wave_colour,3,true)

func background_ripples() -> void:
	# The camera settles before 66s; decorative reception continues through the shot.
	for event in 11:
		var received := event >= 8
		var birth := 6.22+(event-8)*0.12 if received else 5.48+event*0.087
		var lifetime := 1.40 if received else 0.50
		var age := local_time-birth
		if age < 0 or age > lifetime: continue
		var centre := point_at(flight(birth))
		for layer in (2 if received else 3):
			var u := clampf(age/lifetime-layer*0.09,0,1)
			if u <= 0: continue
			var spread := sin(u*PI/2) if received else 1-pow(1-u,3)
			var radius := lerpf(70,860 if received else 790,spread)
			var alpha := 0.08*pow(1-u,0.60)*smoothstep(0,0.08,age) if received else 0.12*pow(1-u,2)
			var colour := Color(1,1,1,alpha)
			draw_arc(centre,radius,0,TAU,96,colour,3,true)

func laser_behind_character() -> void:
	var age := laser_age
	if age < 0 or age > 0.78: return
	# Screen-crossing speed is independent of the remaining gentle follow.
	var left := -position.x-350
	var tip := -position.x+lerpf(-300,2850,unit(0,0.085,age))
	var centre_y := cup_anchor.y+40
	var power := 1.0-smoothstep(0.56,0.78,age)
	var punch := exp(-age/0.11)
	var half_height := 158*(1+0.02*punch)
	for glow in [440.0,390.0,350.0]:
		draw_line(Vector2(left,centre_y),Vector2(tip,centre_y),Color(0.72,0.87,1.0,(0.10+0.008*punch)*power),glow*(1+0.015*punch),true)
	var band := Rect2(Vector2(left,centre_y-half_height),Vector2(maxf(tip-left,0),2*half_height))
	draw_rect(band,Color(0.96,0.985,1.0,power))
	# A displaced, enlarged soft silhouette is clipped onto the light plane.
	# The gap between this cast shadow and the foreground body gives beam depth.
	var projected := Rect2(heroine_origin+Vector2(100,36),heroine_size*1.035)
	var clipped := projected.intersection(band)
	if clipped.has_area():
		var source := Rect2((clipped.position-projected.position)/projected.size*shadow.get_size(),clipped.size/projected.size*shadow.get_size())
		draw_texture_rect_region(shadow,clipped,source,Color(1,1,1,0.82*power))
	# Thin hot edges and a sharp, advancing front keep the pass forceful.
	for edge in [-half_height,half_height]:
		draw_line(Vector2(left,centre_y+edge),Vector2(tip,centre_y+edge),Color(1,1,1,0.85*power),6,true)
	draw_line(Vector2(tip,centre_y-half_height+4),Vector2(tip,centre_y+half_height-4),Color(1,1,1,power),18,true)

func _draw() -> void:
	if local_time < 4.95: return
	laser_behind_character()
	background_ripples()
	# All handset contours appear with the silhouette, with no drawing animation.
	partial(phone_frame,1,BLUE,6)
	partial(phone_speaker,1,BLUE,6)
	partial(phone_home,1,BLUE,6)
	# Only the envelope is drawn inside the phone. It leaves after the draw completes.
	if local_time < 5.17:
		partial(phone_icon,unit(4.95,5.17,local_time),BLUE,6)
	var path := PackedVector2Array()
	for i in 129: path.append(route_at(i/128.0))
	var trace := smoothstep(5.38,5.65,local_time)
	partial(path,flight(local_time),Color(1,1,1,0.74*trace),10)
	# Sample the actual accelerated motion over a 22ms shutter, with broad soft streaks.
	var speed := absf(point_at(flight(travel_time(shot_time+0.001))).x-point_at(flight(travel_time(shot_time-0.001))).x)/0.002
	var blur := smoothstep(2800,10500,speed)
	if blur > 0 and local_time < 6.30:
		var now := point_at(flight(local_time))
		var tail := point_at(flight(travel_time(shot_time-0.022)))
		for band in [36.0,22.0,12.0]:
			draw_line(tail,now,Color(1,1,1,0.035*blur),band,true)
		for exposure in 22:
			packet(travel_time(shot_time-exposure*0.001),0.85*blur/22)
	packet(local_time,1-0.55*blur)
	var hit := unit(6.30,6.58,shot_time)
	var bump := Vector2(4*pow(sin(PI*hit),2),0)
	if heroine:
		draw_texture_rect(shadow,Rect2(heroine_origin+bump+Vector2(20,16),heroine_size),false)
		draw_texture_rect(heroine,Rect2(heroine_origin+bump,heroine_size),false)
		# The final trace meets the cup's closed base; a small punch and return reads as impact.
		if local_time >= 6.30:
			draw_line(cup_anchor-Vector2(35,0),cup_anchor+bump,WHITE,10,true)
			draw_circle(cup_anchor+bump,3.5,BLUE,true)
