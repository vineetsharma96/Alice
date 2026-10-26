import * as THREE from '/vendor/three.module.min.js';
import {OrbitControls} from '/vendor/OrbitControls.js';

// Presentation geometry only. Nothing in this module advances or writes the world.
export class WorldView {
 constructor(host,onSelect,onGround){
  this.host=host;this.onSelect=onSelect;this.onGround=onGround;this.objects=new Map();this.keys=new Set();this.frames=0;this.fps=0;this.intervals=[];this.contextLost=false;this.contextLosses=0;this.quality='low';this.selected=null;
  this.scene=new THREE.Scene();this.scene.background=new THREE.Color('#27353a');this.scene.fog=new THREE.Fog('#27353a',35,90);
  this.camera=new THREE.PerspectiveCamera(42,1,.05,3000);
  this.renderer=new THREE.WebGLRenderer({antialias:false,powerPreference:'low-power',alpha:false});
  this.renderer.outputColorSpace=THREE.SRGBColorSpace;host.append(this.renderer.domElement);
  this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=!matchMedia('(prefers-reduced-motion: reduce)').matches;this.controls.dampingFactor=.1;this.controls.maxPolarAngle=Math.PI*.47;this.controls.minDistance=1.5;this.controls.maxDistance=1500;
  this.scene.add(new THREE.HemisphereLight(0xc9e4e4,0x53675a,2.5));const light=new THREE.DirectionalLight(0xffefd3,2.0);light.position.set(-8,18,12);this.scene.add(light);
  this.geo={box:new THREE.BoxGeometry(1,1,1),body:new THREE.CylinderGeometry(1,1,1,8),head:new THREE.SphereGeometry(1,8,6),rock:new THREE.IcosahedronGeometry(1,0)};
  this.materials=new Map();this.ray=new THREE.Raycaster();this.pointer=new THREE.Vector2();this.plane=new THREE.Plane(new THREE.Vector3(0,1,0),0);
  const ring=new THREE.RingGeometry(.38,.44,32);this.ring=new THREE.Mesh(ring,new THREE.MeshBasicMaterial({color:0xc2e6bd,side:THREE.DoubleSide,depthWrite:false}));this.ring.rotation.x=-Math.PI/2;this.ring.visible=false;this.scene.add(this.ring);
  this.renderer.domElement.addEventListener('pointerdown',e=>{this.down=[e.clientX,e.clientY];});
  this.renderer.domElement.addEventListener('pointerup',e=>this.pick(e));
  this.renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();this.contextLost=true;this.contextLosses++;this.fps=0;this.onContext?.(true);});
  this.renderer.domElement.addEventListener('webglcontextrestored',()=>{this.contextLost=false;this.onContext?.(false);});
  host.addEventListener('keydown',e=>{if(['w','a','s','d','W','A','S','D','Shift'].includes(e.key)){e.preventDefault();this.keys.add(e.key.toLowerCase());}});
  host.addEventListener('keyup',e=>this.keys.delete(e.key.toLowerCase()));host.addEventListener('blur',()=>this.keys.clear());
  this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(host);
  this.visibilityHandler=()=>{this.lastRender=0;this.frames=0;this.fps=0;this.intervals=[];this.windowStart=performance.now();if(document.hidden&&this.raf){cancelAnimationFrame(this.raf);this.raf=null;}else if(!document.hidden&&this.active&&this.alive&&!this.raf)this.raf=requestAnimationFrame(this.loop);};document.addEventListener('visibilitychange',this.visibilityHandler);
  this.last=performance.now();this.lastRender=0;this.windowStart=this.last;this.alive=true;this.active=true;this.loop=this.loop.bind(this);this.raf=requestAnimationFrame(this.loop);
 }
 material(color){if(!this.materials.has(color))this.materials.set(color,new THREE.MeshLambertMaterial({color}));return this.materials.get(color);}
 mesh(group,shape,color,position,scale){const m=new THREE.Mesh(this.geo[shape],this.material(color));m.position.set(...position);m.scale.set(...scale);group.add(m);return m;}
 create(e){
  const g=new THREE.Group();g.userData.id=e.entity_id;g.userData.appearance=`${e.kind}/${e.stage??''}`;const radius=Math.max(.12,e.radius_m||.25);
  if(e.kind==='actor'||e.kind==='operator_avatar'){
   const color=e.kind==='operator_avatar'?'#d9e8d2':e.alive===false?'#746e6d':'#90aea4';
   this.mesh(g,'body',color,[0,.5,0],[radius,.72,radius]);this.mesh(g,'head',color,[0,1.07,0],[.17,.17,.17]);
   g.userData.health=this.mesh(g,'box','#b2d9bc',[0,1.4,0],[.5,.04,.07]);
   g.userData.busy=this.mesh(g,'head','#f0bf78',[.29,1.12,0],[.05,.05,.05]);
  }else if(e.kind==='animal'){
   const hen=['animal-2','animal-4','animal-6'].includes(e.entity_id)||e.species==='reedhen',color=e.alive===false?'#736b62':hen?'#c5a06f':'#b8c2ae';
   this.mesh(g,'head',color,[0,hen?.26:.38,0],hen?[.2,.23,.18]:[.2,.23,.32]);
   this.mesh(g,'head',color,[0,hen?.48:.53,-.19],hen?[.1,.12,.1]:[.12,.14,.16]);
   if(hen)this.mesh(g,'box','#c88748',[0,.47,-.31],[.06,.04,.1]);
   for(const x of [-.12,.12])for(const z of (hen?[0]:[-.18,.18]))this.mesh(g,'body','#726d53',[x,.12,z],[.035,.23,.035]);
  }else if(e.kind==='forage'){
   for(const [x,z] of [[-.2,0],[0,.16],[.2,-.1]])this.mesh(g,'body','#7b9863',[x,.12,z],[.07,.24,.07]);
  }else if(e.kind==='book'){
   this.mesh(g,'box','#d3c5a3',[0,.16,0],[.65,.12,.46]);this.mesh(g,'box','#718b81',[-.3,.17,0],[.06,.15,.48]);
   }else if(e.kind==='thermal_cell'){
    this.mesh(g,'body','#9eaeb3',[0,.35,0],[.35,.7,.35]);this.mesh(g,'body','#435c64',[0,.71,0],[.29,.025,.29]);this.mesh(g,'box','#a37853',[.37,.27,0],[.1,.08,.25]);
   }else if(e.kind==='tree'){
    const stump=e.stage==='stump',mature=e.stage==='mature';
    this.mesh(g,'body',stump?'#72513b':'#79523a',[0,radius*.8,0],[radius*.42,radius*1.8,radius*.42]);
    if(!stump)this.mesh(g,'head',mature?'#5f8c5b':'#789c63',[0,radius*2.1,0],[radius*(mature?1.55:1.05),radius*(mature?1.35:1.0),radius*(mature?1.55:1.05)]);
   }else if(['construction','storage_box','trough','fence','gate'].includes(e.kind)){
    const colors={construction:'#b49e79',storage_box:'#a87545',trough:'#778e95',fence:'#927052',gate:'#ac8c68'};
    this.mesh(g,'box',colors[e.kind],[0,.35,0],[.9,.7,e.kind==='fence'||e.kind==='gate'?.25:.9]);
   }else if(e.kind==='tool'){
    this.mesh(g,'box','#98704c',[0,.15,0],[.5,.08,.08]);this.mesh(g,'box','#969e9e',[.2,.15,0],[.16,.2,.12]);
   }else if(e.kind==='spent_tool'||e.kind==='cancelled_site'){
    g.visible=false;
   }else if(e.kind==='food'||e.kind==='water'){
    const color=e.kind==='food'?'#b99c6b':'#688d9b';this.mesh(g,'body',color,[0,.13,0],[.5,.26,.5]);
    this.mesh(g,'box',e.kind==='food'?'#dcc391':'#9db9bd',[0,.28,0],[.23,.04,.23]);
   }else if(['wood','fiber','wood_offcut','stone'].includes(e.kind)){
    const colors={wood:'#a87545',fiber:'#d0b27a',wood_offcut:'#bd8a55',stone:'#8c9698'};
    this.mesh(g,'box',colors[e.kind],[0,radius*.55,0],[radius*1.8,radius*.9,radius*1.2]);
   }else{
   this.mesh(g,e.kind==='rock'?'rock':'box',e.kind==='inert_material'?'#b3b5a4':'#748787',[0,radius*.55,0],[radius*1.5,radius*1.1,radius*1.5]);
  }
  this.scene.add(g);return g;
 }
 update(snapshot,selected){
  this.snapshot=snapshot;this.selected=selected;const b=snapshot.world_bounds_m;
  if(!this.bounds||this.bounds.width!==b.width||this.bounds.height!==b.height){
   if(this.floor){this.scene.remove(this.floor,this.grid);this.grid.geometry.dispose();this.grid.material.dispose();}
   this.bounds=b;this.floor=new THREE.Mesh(this.geo.box,this.material('#3e5352'));this.floor.scale.set(b.width,.18,b.height);this.floor.position.set(b.width/2,-.12,-b.height/2);this.scene.add(this.floor);
   const size=Math.max(b.width,b.height);this.grid=new THREE.GridHelper(size,Math.min(64,Math.ceil(size)),0x79938a,0x536d65);this.grid.position.set(b.width/2,-.015,-b.height/2);this.scene.add(this.grid);this.fit();
  }
  const live=new Set();for(const e of snapshot.entities){
   live.add(e.entity_id);let g=this.objects.get(e.entity_id);if(g&&g.userData.appearance!==`${e.kind}/${e.stage??''}`){this.scene.remove(g);this.objects.delete(e.entity_id);g=null;}if(!g){g=this.create(e);this.objects.set(e.entity_id,g);}
   g.position.set(e.position_m[0],0,-e.position_m[1]);g.visible=e.present!==false&&!['spent_tool','cancelled_site'].includes(e.kind);if(e.kind==='forage')g.scale.setScalar(Math.max(.05,Math.min(1,Number(e.mass_ug)/2e9)));if(e.kind==='animal'){const isHen=['animal-2','animal-4','animal-6'].includes(e.entity_id)||e.species==='reedhen';g.rotation.z=e.alive===false?Math.PI/2:0;for(const child of g.children)if(child.geometry===this.geo.head)child.material=this.material(e.alive===false?'#736b62':isHen?'#c5a06f':'#b8c2ae');}if(e.kind==='gate')g.rotation.y=e.radius_m===0?Math.PI/2:0;
   if(g.userData.health){g.userData.health.scale.x=.5*(e.body?.health??1);g.userData.health.visible=e.alive!==false;g.userData.busy.visible=snapshot.outstanding_actions.some(a=>a.agent_id===e.entity_id);if(e.kind==='actor'){const m=this.material(e.alive===false?'#746e6d':'#90aea4');g.children[0].material=m;g.children[1].material=m;}}
  }
  for(const [id,g] of this.objects)if(!live.has(id)){this.scene.remove(g);this.objects.delete(id);}
  this.select(selected);
 }
 select(id){this.selected=id;const g=this.objects.get(id);this.ring.visible=!!g&&g.visible;if(g)this.ring.position.set(g.position.x,.012,g.position.z);}
 fit(){if(!this.bounds)return;const b=this.bounds,size=Math.max(b.width,b.height),half=Math.min(this.camera.fov*Math.PI/360,Math.atan(Math.tan(this.camera.fov*Math.PI/360)*this.camera.aspect)),distance=Math.hypot(b.width,b.height)*.52/Math.sin(half);this.controls.target.set(b.width/2,0,-b.height/2);this.camera.position.copy(this.controls.target).add(new THREE.Vector3(.78,.95,.92).normalize().multiplyScalar(distance));this.camera.far=Math.max(100,size*8);this.camera.updateProjectionMatrix();this.controls.update();}
 focus(id){const g=this.objects.get(id);if(!g)return;const delta=this.camera.position.clone().sub(this.controls.target).normalize().multiplyScalar(5);this.controls.target.copy(g.position).add(new THREE.Vector3(0,.5,0));this.camera.position.copy(this.controls.target).add(delta);this.controls.update();}
 resize(){const w=this.host.clientWidth,h=this.host.clientHeight;if(!w||!h)return;const scale=this.quality==='low'?.8:1;this.renderer.setPixelRatio(Math.min(devicePixelRatio,1.25)*scale);this.renderer.setSize(w,h);this.camera.aspect=w/h;this.camera.updateProjectionMatrix();this.fit();}
  setQuality(value){this.quality=value;this.visibilityHandler();this.resize();}
  setActive(value){if(this.active===value)return;this.active=value;if(value&&this.alive&&!this.raf){this.last=performance.now();this.lastRender=0;this.windowStart=this.last;this.raf=requestAnimationFrame(this.loop);}if(!value&&this.raf){cancelAnimationFrame(this.raf);this.raf=null;}}
 pick(event){
  if(!this.down||Math.hypot(event.clientX-this.down[0],event.clientY-this.down[1])>5||event.button!==0)return;
  const r=this.renderer.domElement.getBoundingClientRect();this.pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);this.ray.setFromCamera(this.pointer,this.camera);
  if(this.groundPicking){const p=new THREE.Vector3();if(this.ray.ray.intersectPlane(this.plane,p)&&p.x>=0&&p.x<=this.bounds.width&&-p.z>=0&&-p.z<=this.bounds.height)this.onGround([p.x,-p.z]);return;}
  for(const hit of this.ray.intersectObjects([...this.objects.values()].filter(g=>g.visible),true)){let g=hit.object;while(g&&!g.userData.id)g=g.parent;if(g){this.onSelect(g.userData.id);break;}}
 }
 loop(now){
   if(!this.alive||!this.active){this.raf=null;return;}this.raf=requestAnimationFrame(this.loop);const delta=Math.min(.05,(now-this.last)/1000);this.last=now;
  if(document.hidden||this.contextLost)return;const frameMs=this.quality==='low'?1000/30:1000/60;if(now-this.lastRender<frameMs-1)return;
  const motionDelta=this.lastRender?Math.min(.05,(now-this.lastRender)/1000):delta;
  if(this.lastRender){this.intervals.push(now-this.lastRender);if(this.intervals.length>300)this.intervals.shift();}this.lastRender=now;
  if(this.keys.size){const f=this.camera.getWorldDirection(new THREE.Vector3());f.y=0;f.normalize();const right=new THREE.Vector3().crossVectors(f,new THREE.Vector3(0,1,0));const move=new THREE.Vector3();if(this.keys.has('w'))move.add(f);if(this.keys.has('s'))move.sub(f);if(this.keys.has('d'))move.add(right);if(this.keys.has('a'))move.sub(right);move.normalize().multiplyScalar(motionDelta*(this.keys.has('shift')?10:4));this.camera.position.add(move);this.controls.target.add(move);}
  this.controls.update();this.renderer.render(this.scene,this.camera);this.frames++;
  if(now-this.windowStart>=1000){this.fps=this.frames*1000/(now-this.windowStart);this.frames=0;this.windowStart=now;}
 }
 metrics(){const sorted=[...this.intervals].sort((a,b)=>a-b);const gl=this.renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');return {fps:this.fps,frame_ms_p50:sorted[Math.floor(sorted.length*.5)]??null,frame_ms_p95:sorted[Math.floor(sorted.length*.95)]??null,draw_calls:this.renderer.info.render.calls,triangles:this.renderer.info.render.triangles,geometries:this.renderer.info.memory.geometries,textures:this.renderer.info.memory.textures,quality:this.quality,pixel_ratio:this.renderer.getPixelRatio(),context_lost:this.contextLost,context_losses:this.contextLosses,renderer:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),canvas:[this.renderer.domElement.width,this.renderer.domElement.height],physics_dimensions:2,objects:this.objects.size};}
 project(id){const g=this.objects.get(id);if(!g)return null;const p=g.position.clone().add(new THREE.Vector3(0,.5,0)).project(this.camera),r=this.renderer.domElement.getBoundingClientRect();return {x:r.left+(p.x+1)*r.width/2,y:r.top+(1-p.y)*r.height/2};}
  dispose(){this.alive=false;cancelAnimationFrame(this.raf);this.raf=null;document.removeEventListener('visibilitychange',this.visibilityHandler);this.resizeObserver.disconnect();this.controls.dispose();for(const g of Object.values(this.geo))g.dispose();for(const m of this.materials.values())m.dispose();this.ring.geometry.dispose();this.ring.material.dispose();this.grid?.geometry.dispose();this.grid?.material.dispose();this.renderer.dispose();}
}
