const _={},post=(d)=>fetch('',{method:'POST',body:JSON.stringify(d)})
const load=()=>fetch('status').then(r=>r.json()).then(r=>Object.assign(_,r))
const gui=new dat.GUI(),misc=gui.addFolder('misc'),cam=gui.addFolder('camera')
const reloadImage=()=>{document.getElementById('s').src=`stream.mjpg?${new Date().getTime()}`}
const updateTitle=()=>{document.title=`fps: ${_.camera.framerate} exp: ${_.camera.exposure_speed}`}
const refresh=()=>load().then(()=>{updateTitle();[gui,cam].map(i=>i.__controllers.map(j=>j.updateDisplay()))})
const s={stream:[],lapse:[],interval:[1,300,1]},f={refresh,reloadImage,shutdown:()=>fetch('shutdown')}
const rotation=[[0,180]],shutter_speed=[0,100000,1],brightness=[0,100,1],contrast=[-100,100,1]
const exposure_mode=[['off','auto','night','sports','beach','backlight','spotlight','antishake']]
const meter_mode=[['average','spot','backlit','matrix']],iso=[[0,1,2,3.2,4,5,6.4,8].map(i=>i*100)]
const awb_mode=[['off','auto','fix','sunlight','cloudy','shade','tungsten','horizon','incandescent']]
const c={rotation,brightness,contrast,iso,exposure_mode,meter_mode,awb_mode,shutter_speed}
load().then(()=>{Object.keys(f).map(k=>misc.add(f,k))
 Object.keys(s).map(k=>gui.add(_,k,...s[k]).onFinishChange((v)=>post({[k]:v})))
 _.camera&&Object.keys(c).map(k=>cam.add(_.camera,k,...c[k]).onFinishChange((v)=>post({camera:{[k]:v}})))
})
