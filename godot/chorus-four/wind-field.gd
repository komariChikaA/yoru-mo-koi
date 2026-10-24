extends "res://hair-sway.gd"
## Directional gusts advect through the picture; spring response lags at tips.
## 100% is a 45 degree total chain bend, never 45 degrees per joint.
@export var wind_direction:=Vector2(-1.0,-0.24)
@export_range(0.0,1.0,0.01) var turbulence:=0.18
@export var propagation_speed:=850.0

func _joint_weight(index: int, count: int) -> float:
	return pow(float(index)/float(count-1), 0.8)

func field(t:float,point:Vector2,seed:float) -> float:
	var travel:=point.dot(wind_direction.normalized())/propagation_speed
	var phase:=TAU*(t-travel)/cycle
	# Positive prevailing wind with two unequal gusts and coherent eddies.
	var gust:=pow(0.5+0.5*sin(phase+0.4),3.0)
	var eddy:=sin(2.0*phase+seed)*0.6+sin(3.0*phase-seed*0.7)*0.4
	return clampf(0.20+0.64*gust+turbulence*eddy,0.03,1.0)

func _bake(data:Dictionary) -> void:
	var steps:=roundi(cycle*sample_rate)
	var count:int=data.bones.size()
	var angles:=PackedFloat32Array();angles.resize(count)
	var velocity:=PackedFloat32Array();velocity.resize(count)
	var poses:Array[PackedFloat32Array]=[]
	var maximum:=deg_to_rad(45.0)*float(data.definition.sway_percent)/100.0
	var seed:=float(data.definition.phase)
	var total_weight:=0.0
	for i in range(1,count):total_weight+=_joint_weight(i,count)
	var peak:=0.0
	for step in range(steps*5+1):
		var t:=float(step%steps)/sample_rate
		for i in range(1,count):
			var u:=float(i)/float(count-1)
			var response:=float(data.definition.get("response",7.0))*(1.15-0.30*u)
			var damping:=1.65*response
			var wind:=field(t-0.11*u,data.points[i],seed)
			var tangent:Vector2=data.points[i]-data.points[i-1]
			var sign_turn:=signf(tangent.cross(wind_direction))
			var target:=sign_turn*maximum*_joint_weight(i,count)/total_weight*wind
			# A critically damped angular spring avoids metronomic reversals.
			velocity[i]+=(response*response*(target-angles[i])-damping*velocity[i])/sample_rate
			angles[i]+=velocity[i]/sample_rate
		if step>=steps*4:
			poses.append(angles.duplicate())
			var bend:=0.0
			for value in angles:bend+=absf(value)
			peak=maxf(peak,bend)
	data.stack.enabled=false
	for i in count:
		data.skeleton.set_bone_local_pose_override(i,Transform2D.IDENTITY,0.0,false)
		data.bones[i].rotation=0.0
	var seam:=0.0
	for i in count:seam=maxf(seam,absf(poses[-1][i]-poses[0][i]))
	poses[-1]=poses[0]
	data.poses=poses
	print("WIND_BAKE %s region=%s percent=%.1f limit_deg=%.2f peak_deg=%.2f seam_deg=%.6f"%[data.definition.name,data.definition.region,data.definition.sway_percent,rad_to_deg(maximum),rad_to_deg(peak),rad_to_deg(seam)])
