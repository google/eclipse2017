import ephem
import math
deg = math.degrees
def get_lune(sun, moon):
    r_sun=sun.size/2
    r_moon=moon.size/2
    s=math.degrees(ephem.separation((sun.az, sun.alt), (moon.az, moon.alt)))*60*60

    ## Calculate the size of the lune (http://mathworld.wolfram.com/Lune.html) in arcsec^2
    if s<(r_moon+r_sun):
        x = (r_sun+r_moon+s)*(r_moon+s-r_sun)*(s+r_sun-r_moon)*(r_sun+r_moon-s)
        lunedelta=0.25*math.sqrt(abs(x))
    else: ### If s>r_moon+r_sun there is no eclipse taking place
        lunedelta=None
        percent_eclipse=0
    if lunedelta:
        x = ((r_moon*r_moon)-(r_sun*r_sun)-(s*s))
        y = ((r_moon*r_moon)+(s*s)-(r_sun*r_sun))
        # Total eclipse
        if x/(2*r_sun*s) > 1:
            return 100.
        else:
            lune_area=2*lunedelta + r_sun*r_sun*(math.acos(x/(2*r_sun*s))) - r_moon*r_moon*(math.acos(y/(2*r_moon*s)))
            percent_eclipse=(1-(lune_area/(math.pi*r_sun*r_sun)))*100 # Calculate percentage of sun's disc eclipsed using lune area and sun size
            return percent_eclipse
    else:
        return 0.
