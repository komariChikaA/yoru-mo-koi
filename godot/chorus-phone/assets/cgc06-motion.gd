extends RefCounted

const ENTRY_RATE:=0.85
const SLOW_RATE:=0.08
const HOLD_SECONDS:=0.08
const DECEL_SECONDS:=1.50
const SLOW_START:=HOLD_SECONDS+DECEL_SECONDS

static func progress(seconds:float) -> float:
	# Use a gentler shared entry, spreading braking across the closeup.
	# Integrate a smoothstep velocity ramp; the slow drift stays visible in blur.
	if seconds<=HOLD_SECONDS: return ENTRY_RATE*seconds
	var elapsed:=seconds-HOLD_SECONDS
	var u:=clampf(elapsed/DECEL_SECONDS,0.0,1.0)
	var eased_distance:=DECEL_SECONDS*(u-u*u*u+0.5*u*u*u*u)
	return ENTRY_RATE*HOLD_SECONDS+SLOW_RATE*elapsed+(ENTRY_RATE-SLOW_RATE)*eased_distance

static func center(seconds:float) -> Vector2:
	return Vector2(430,560).lerp(Vector2(765,430),progress(seconds))

static func zoom(seconds:float) -> float:
	# Finish zoom together with braking so it cannot speed up the slow tail.
	return lerpf(3.15,3.50,smoothstep(0.0,SLOW_START,seconds))
