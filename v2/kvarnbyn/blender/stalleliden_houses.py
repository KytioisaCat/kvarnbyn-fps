"""M25: observed 2017 appearance, estimated metric authoring on original OSM L.

See reference/stalleliden-hus. No third-party photo pixels. Visible west gable,
south windows/dormer and porch replace the automatic two-storey rectangle.
"""
import math, random
from mathutils import Vector
from modelkit import Frame, color
from blender_materials import solid_material, pbr_material


def build_m25(K, M, ground, b, spec):
    fr=Frame(b['centroid_xz'],b['major_axis_xz']);base=b['base_y_m'];eave=spec['eave_m'];name='Stalleliden_M25'
    wall=M['wall'](b);trim=solid_material('M25_offwhite_trim',color(spec['trim_color']),.8)
    sash=solid_material('M25_offwhite_sash',color(spec['sash_color']),.7)
    metal=solid_material('M25_grey_sheet',color('#858c8a'),.58,.35)
    dormer_side=solid_material('M25_dormer_side',color('#ac8c7e'),.85)
    dormer_roof=solid_material('M25_dormer_sheet',color('#93776b'),.65,.2)
    mortar=solid_material('M25_dark_granite_joints',color('#414943'),.96)
    stones=[pbr_material('rock','M25_granite_'+str(i),color(c),normal_strength=.45,roughness=.94) for i,c in enumerate(['#747775','#5f6462','#85877f','#555a58','#72746f'])]
    for m in stones:m['tile_size_m']=.75
    main,annex=spec['main'],spec['annex']
    def ab(q):
        dx,dz=q[0]-fr.cx,q[1]-fr.cz
        return (dx*fr.u[0]-dz*fr.u[1],dx*fr.v[0]-dz*fr.v[1])
    def roofh(volume,a,c):
        half=(volume['b1']-volume['b0'])/2
        return eave+volume['rise_m']*max(0.,1-abs(c-volume['ridge_b'])/half)
    def cleanface(label,mat,pts,both=False,col=False):
        q=[]
        for p in pts:
            if not q or math.dist(q[-1],p)>1e-7:q.append(p)
        if len(q)>2 and math.dist(q[0],q[-1])<1e-7:q.pop()
        if len(q)<3:return
        K.face(label,mat,q)
        if both:K.face(label,mat,q[::-1])
        if col:K.face('COL_'+label,M['collision'],q)
    def opening(at,o):
        s,bt,w,h=o[:4];kind=o[4]
        u=(at(1,0,0)[0]-at(0,0,0)[0],at(1,0,0)[1]-at(0,0,0)[1])
        v=(at(0,1,0)[0]-at(0,0,0)[0],at(0,1,0)[1]-at(0,0,0)[1])
        if kind=='door':
            K.box(name+'_Door',trim,at(s,.055,bt+h/2),(w,.085,h),u)
            for ss in (-w/2,w/2):K.box(name+'_Door_trim',trim,at(s+ss,.13,bt+h/2),(.085,.14,h+.12),u)
            for hh in (bt,bt+h):K.box(name+'_Door_trim',trim,at(s,.13,hh),(w+.12,.14,.085),u)
            for hh in (bt+.25,bt+.78,bt+1.35,bt+1.85):K.box(name+'_Door_panels',sash,at(s,.115,hh),(w-.18,.035,.035),u)
            K.beam(name+'_Door_handle',M['iron'],at(s+w*.32,.17,bt+.92),at(s+w*.32,.17,bt+1.07),.015,6)
        else:
            # M25 has shallow painted frames, rather than the generic kit's
            # deep ornamental caps/sills. Small attic lights are single-pane.
            K.face(name+'_Window_glass',M['glass_dark'],[at(s-w/2,.035,bt),at(s+w/2,.035,bt),at(s+w/2,.035,bt+h),at(s-w/2,.035,bt+h)])
            for ss in (-w/2,w/2):K.box(name+'_Window_trim',trim,at(s+ss,.055,bt+h/2),(.085,.075,h+.12),u,v)
            for hh in (bt,bt+h):K.box(name+'_Window_trim',trim,at(s,.055,hh),(w+.12,.075,.085),u,v)
            if w>.75:K.box(name+'_Window_sash',sash,at(s,.075,bt+h/2),(.045,.035,h-.08),u,v)
            if h>1.1:K.box(name+'_Window_sash',sash,at(s,.075,bt+h*.5),(w-.08,.035,.035),u,v)
            K.box(name+'_Window_sill',trim,at(s,.07,bt-.06),(w+.16,.14,.055),u,v)
    def elevation(at,L,top,openings,label,mat=wall,ridges=()):
        # Roof kinks and opening edges are explicit face boundaries.
        cuts=sorted(set([0.,L]+[max(0.,min(L,x)) for s,y,w,h,*_ in openings for x in (s-w/2-.04,s+w/2+.04)]+list(ridges)))
        levels=sorted(set([0.,max(top(s) for s in cuts)]+[y for s,bt,w,h,*_ in openings for y in (bt-.04,bt+h+.04)]))
        for left,right in zip(cuts,cuts[1:]):
            if right-left<.001:continue
            for lo,hi in zip(levels,levels[1:]):
                if any(s-w/2-.041<(left+right)/2<s+w/2+.041 and bt-.041<(lo+hi)/2<bt+h+.041 for s,bt,w,h,*_ in openings):continue
                a,c=left,right;ha,hc=top(a),top(c)
                if max(ha,hc)<=lo+.001:continue
                if ha<lo:
                    a+=(c-a)*(lo-ha)/(hc-ha);ha=lo
                if hc<lo:
                    c=a+(c-a)*(ha-lo)/(ha-hc);hc=lo
                pts=[at(a,0,lo),at(c,0,lo),at(c,0,min(hi,hc)),at(a,0,min(hi,ha))]
                cleanface(label,mat,pts,both=True)
        for j in range(math.ceil(L/.18)):
            s=(j+.5)*L/math.ceil(L/.18);intervals=[(0.,top(s))]
            for centre,bt,w,h,*_ in openings:
                if abs(s-centre)<w/2+.12:
                    intervals=[(lo,min(hi,bt-.12)) for lo,hi in intervals if lo<bt-.12]+[(max(lo,bt+h+.12),hi) for lo,hi in intervals if hi>bt+h+.12]
            for lo,hi in intervals:
                if hi-lo>.02:K.beam(label+'_Locklist',mat,at(s,.045,lo),at(s,.045,hi),.014,4)
        for o in openings:opening(at,o)
    poly=list(b['build_footprint_xz'])
    if sum(a[0]*c[1]-c[0]*a[1] for a,c in zip(poly,poly[1:]+poly[:1]))>0:poly.reverse()
    for edge,(a,c) in enumerate(zip(poly,poly[1:]+poly[:1])):
        A=Vector((a[0],-a[1]));B=Vector((c[0],-c[1]));v=B-A;L=v.length;u=(v.x/L,v.y/L);out=(u[1],-u[0])
        at=lambda s,d,h:(A.x+u[0]*s+out[0]*d,A.y+u[1]*s+out[1]*d,base+h)
        aa,bb=ab(a),ab(c);mid=((aa[0]+bb[0])/2,(aa[1]+bb[1])/2)
        volume=main if mid[0]<main['a1']+.001 else annex
        top=lambda s:roofh(volume,aa[0]+(bb[0]-aa[0])*s/L,aa[1]+(bb[1]-aa[1])*s/L)
        ridges=[]
        if abs(bb[1]-aa[1])>.1:
            t=(volume['ridge_b']-aa[1])/(bb[1]-aa[1])
            if 0<t<1:ridges.append(t*L)
        def along(a_,b_):
            q=fr.p(a_,b_,base);return (q[0]-A.x)*u[0]+(q[1]-A.y)*u[1]
        openings=[]
        if abs(mid[0]-main['a0'])<.03:
            for c_ in (-2.48,1.82):openings.append((along(main['a0'],c_),.65,1.12,1.65,'window'))
            openings.append((along(main['a0'],main['ridge_b']),3.55,1.2,1.25,'window'))
            for c_ in (main['ridge_b']-2.6,main['ridge_b']+2.6):openings.append((along(main['a0'],c_),3.5,.48,.60,'window'))
        elif abs(mid[1]-main['b0'])<.03:
            for a_ in (-2.9,-.5,1.7):
                openings.append((along(a_,main['b0']),.65,1.05,1.65,'window'))
                openings.append((along(a_,main['b0']),2.55,.95,.26,'window'))
        elif abs(mid[1]-annex['b0'])<.03 and mid[0]>main['a1']:
            d=spec['door'];openings.append((along(d['a'],d['b']),.03,d['width_m'],d['height_m'],'door'))
        elif mid[1]>4.0:
            for a_ in (-2.4,.8,3.8):
                s=along(a_,4.129)
                if .7<s<L-.7:openings.append((s,.9,1.0,1.35,'window'))
        elif mid[0]>5.0:
            openings.append((L*.5,.85,1.0,1.35,'window'))
        elevation(at,L,top,openings,name+'_Panel',ridges=ridges)
        # Foundation follows local ground, rather than a tall global-min box.
        n=max(1,math.ceil(L/.45))
        for i in range(n):
            s0,s1=L*i/n,L*(i+1)/n
            q0,q1=at(s0,0,0),at(s1,0,0)
            low0=min(base-.2,ground(q0[0],-q0[1])-.22);low1=min(base-.2,ground(q1[0],-q1[1])-.22)
            cleanface(name+'_Foundation',mortar,[at(s0,0,low0-base),at(s1,0,low1-base),at(s1,0,.04),at(s0,0,.04)],both=True)
            cleanface('COL_'+name+'_Body',M['collision'],[at(s0,0,low0-base),at(s1,0,low1-base),at(s1,0,top(s1)),at(s0,0,top(s0))])
        low=min(ground(*a),ground(*c))-.25-base
        # Irregular, non-uniform fieldstone faces with small dark joints.
        # Course/stone dimensions are authored estimates, not surveyed blocks.
        rng=random.Random(2500+edge)
        for row in range(max(1,math.ceil(-low/.36))):
            ytop=-row*.36;yb=ytop-.34;left=-rng.uniform(.1,.65)
            while left<L:
                right=left+rng.uniform(.42,1.05);l,r=max(0,left),min(L,right-.025)
                left=right
                if r-l<.04:continue
                t0,t1=min(.015,ytop+rng.uniform(-.045,.035)),min(.015,ytop+rng.uniform(-.045,.035))
                floor0=min(-.25,ground(at(l,0,0)[0],-at(l,0,0)[1])-base-.18)
                floor1=min(-.25,ground(at(r,0,0)[0],-at(r,0,0)[1])-base-.18)
                lo0=max(yb+rng.uniform(-.03,.025),floor0);lo1=max(yb+rng.uniform(-.03,.025),floor1)
                if min(lo0,lo1)>=min(t0,t1):continue
                lo0=min(lo0,t0-.015);lo1=min(lo1,t1-.015)
                bevel=min(.07,(r-l)*.12,(min(t0,t1)-max(lo0,lo1))*.2)
                bevel=max(.002,bevel);depth=rng.uniform(.021,.044)
                outline=[(l+bevel,lo0),(r-bevel,lo1),(r,lo1+bevel),(r,t1-bevel),(r-bevel,t1),(l+bevel,t0),(l,t0-bevel),(l,lo0+bevel)]
                cleanface(name+'_Granite_blocks',rng.choice(stones),[at(ss,depth,hh) for ss,hh in outline],both=True)
        for s in (0,L):K.box(name+'_Corners',trim,at(s,.07,eave/2),(.11,.11,eave),u)
    # Two estimated roof volumes clipped to the original L subdivision.
    for label,volume,material in [('main',main,metal),('annex',annex,M['roof'])]:
        a0,a1=volume['a0']-.18,volume['a1']+.18;b0,b1=volume['b0']-.18,volume['b1']+.18;r=volume['ridge_b']
        for c0,c1 in [(b0,r),(r,b1)]:
            pts=[fr.p(a0,c0,base+roofh(volume,a0,c0)),fr.p(a1,c0,base+roofh(volume,a1,c0)),fr.p(a1,c1,base+roofh(volume,a1,c1)),fr.p(a0,c1,base+roofh(volume,a0,c1))]
            if (Vector(pts[1])-Vector(pts[0])).cross(Vector(pts[2])-Vector(pts[0])).z<0:pts.reverse()
            cleanface(name+'_Roof_'+label,material,pts,col=True)
        for a_ in (a0,a1):
            for c_ in (b0,b1):K.beam(name+'_Bargeboards',trim,fr.p(a_,c_,base+roofh(volume,a_,c_)),fr.p(a_,r,base+roofh(volume,a_,r)),.065,4)
        for c_ in (b0,b1):K.beam(name+'_Gutters',trim,fr.p(a0,c_,base+eave-.08),fr.p(a1,c_,base+eave-.08),.055,8)
        if label=='main':
            for i in range(math.ceil((a1-a0)/.55)):
                a_=a0+i*.55
                for c_ in (b0,b1):K.beam(name+'_Roof_seams',metal,fr.p(a_,c_,base+roofh(volume,a_,c_)+.015),fr.p(a_,r,base+roofh(volume,a_,r)+.015),.01,4)
    # Close the visible attic step where the two pitched roofs meet.
    cuts=[annex['b0'],main['ridge_b'],annex['ridge_b'],annex['b1']]
    for c0,c1 in zip(cuts,cuts[1:]):
        h0,h1=roofh(main,main['a1'],c0),roofh(main,main['a1'],c1)
        l0,l1=roofh(annex,main['a1'],c0),roofh(annex,main['a1'],c1)
        pts=[fr.p(main['a1'],c0,base+l0),fr.p(main['a1'],c1,base+l1),fr.p(main['a1'],c1,base+h1),fr.p(main['a1'],c0,base+h0)]
        cleanface(name+'_Attic_join',wall,pts,both=True,col=True)
    # Observed south-facing dormer: white front, muted warm cheeks and shed roof.
    d=spec['dormer'];a0,a1=d['a']-d['width_m']/2,d['a']+d['width_m']/2;front,back=d['front_b'],d['back_b']
    frontlow=roofh(main,0,front)
    at=lambda s,o,h:fr.p(d['a']+s,front-o,base+h)
    # Elevation uses relative height from roof contact for this separate facade.
    atd=lambda s,o,h:at(s-d['width_m']/2,o,frontlow+h)
    elevation(atd,d['width_m'],lambda s:d['front_top_m']-frontlow,[(d['width_m']/2,4.0-frontlow,1.8,.78,'window')],name+'_Dormer_front',mat=wall)
    for a_ in (a0,a1):
        cleanface(name+'_Dormer_cheeks',dormer_side,[fr.p(a_,front,base+frontlow),fr.p(a_,back,base+roofh(main,a_,back)),fr.p(a_,back,base+d['back_top_m']),fr.p(a_,front,base+d['front_top_m'])],both=True,col=True)
    cleanface(name+'_Dormer_roof',dormer_roof,[fr.p(a0-.1,front-.1,base+d['front_top_m']),fr.p(a1+.1,front-.1,base+d['front_top_m']),fr.p(a1+.1,back,base+d['back_top_m']),fr.p(a0-.1,back,base+d['back_top_m'])],both=True,col=True)
    # Small half-round vent at the west gable's peak.
    centre=Vector(fr.p(main['a0']-.055,main['ridge_b'],base+5.60));u=Vector((*fr.v,0));z=Vector((0,0,1));n=Vector((-fr.u[0],-fr.u[1],0))
    arc=[centre+u*math.cos(i*math.pi/20)*.23+z*math.sin(i*math.pi/20)*.23 for i in range(21)]
    cleanface(name+'_Attic_vent',M['glass_dark'],arc,both=True)
    for a_,b_ in zip(arc,arc[1:]):K.beam(name+'_Vent_trim',trim,a_+n*.025,b_+n*.025,.022,6)
    K.beam(name+'_Vent_trim',trim,arc[0]+n*.025,arc[-1]+n*.025,.022,6)
    for v in (-.10,0,.10):K.beam(name+'_Vent_trim',trim,centre+u*v+n*.03,centre+u*v+n*.03+z*math.sqrt(.23**2-v*v),.009,4)
    # Small open entry hood; it leaves the walk corridor and door approach clear.
    d=spec['door'];hoodfront=d['b']-.82;hoodback=d['b']+.12
    for a_ in (d['a']-.68,d['a']+.68):
        K.beam(name+'_Porch_posts',trim,fr.p(a_,hoodfront,base),fr.p(a_,hoodfront,base+2.22),.045,6)
        K.beam('COL_'+name+'_Porch_posts',M['collision'],fr.p(a_,hoodfront,base),fr.p(a_,hoodfront,base+2.22),.045,6)
    for sign in (-1,1):
        pts=[fr.p(d['a'],hoodfront-.1,base+2.55),fr.p(d['a']+sign*.80,hoodfront-.1,base+2.22),fr.p(d['a']+sign*.80,hoodback,base+2.22),fr.p(d['a'],hoodback,base+2.55)]
        if (Vector(pts[1])-Vector(pts[0])).cross(Vector(pts[2])-Vector(pts[0])).z<0:pts.reverse()
        cleanface(name+'_Porch_roof',metal,pts,both=True,col=True)
    for a_,c_ in [(main['a0']-.09,main['b0']-.09),(annex['a1']+.09,annex['b0']-.09)]:
        x,z_=fr.xz(a_,c_);K.beam(name+'_Downpipes',trim,fr.p(a_,c_,ground(x,z_)+.05),fr.p(a_,c_,base+eave),.045,8)
    roofbase=base+roofh(annex,3.8,annex['ridge_b'])
    K.box(name+'_Chimney',M['rust'],fr.p(3.8,annex['ridge_b'],roofbase+.48),(.52,.55,1.35),fr.u)
    K.box('COL_'+name+'_Chimney',M['collision'],fr.p(3.8,annex['ridge_b'],roofbase+.48),(.52,.55,1.35),fr.u)
    K.box(name+'_Chimney_cap',M['coping'],fr.p(3.8,annex['ridge_b'],roofbase+1.19),(.65,.68,.09),fr.u)
