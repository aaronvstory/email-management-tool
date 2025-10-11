Create a complete production-grade 3D Flappy Bird implementation using Three.js with the following comprehensive specifications:

**Physics & Core Mechanics:**
Implement a gravity-based physics engine with configurable downward acceleration (default 0.4 units/frame), upward impulse on flap (default -8 units/frame), and terminal velocity constraints. Add pixel-perfect collision detection using bounding box intersection tests between bird geometry and pipe meshes. Include velocity damping for realistic air resistance and rotation interpolation that tilts the bird based on vertical velocity (-90° to +30° range).

**3D Asset Pipeline:**
Create a low-poly bird model using BufferGeometry with animated wing segments (6-frame flap cycle at 10fps). Build procedurally generated pipes using CylinderGeometry with PBR materials (roughness: 0.6, metalness: 0.2) and normal maps for surface detail. Implement a three-layer parallax background using TextureLoader for clouds (0.2x speed), mountains (0.5x speed), and ground (1.0x speed). Add HDR environment mapping using PMREMGenerator for realistic reflections.

**Advanced Rendering:**
Configure WebGLRenderer with antialias, alpha, and logarithmicDepthBuffer enabled. Implement a dual-light setup: HemisphereLight (sky: 0xaaccff, ground: 0xf4e99b, intensity: 0.6) and DirectionalLight (color: 0xffffff, intensity: 0.8, castShadow: true with 2048x2048 shadow map). Add post-processing using EffectComposer with UnrealBloomPass (strength: 0.3, radius: 0.8, threshold: 0.6) and FXAA for anti-aliasing. Include dynamic time-of-day lighting that transitions between dawn (score 0-10), day (11-30), dusk (31-50), and night (51+) with color temperature shifts.

**Particle Systems:**
Implement a trail emitter using Points with BufferGeometry that spawns 5 particles per frame behind the bird, each with exponential alpha decay (lifetime: 30 frames) and upward drift velocity. Add collision burst effects using SphereGeometry instances (count: 20, initial velocity: radial 5-10 units/sec, lifetime: 15 frames). Create score popup particles using TextGeometry with scale animation (ease-out-back, duration: 500ms) and vertical translation (+50 units).

**Audio Architecture:**
Integrate Web Audio API with AudioContext, GainNode for master volume control, and PannerNode for 3D positional audio. Load audio buffers using fetch() + decodeAudioData() for: flap sound (playbackRate: 0.9-1.1 randomized), score ding (440Hz sine wave, duration: 150ms), collision impact (brown noise burst, 200ms), and ambient wind loop (volume: 0.15, stereo widening). Add audio sprite batching to minimize HTTP requests.

**Game State Machine:**
Implement a finite state machine with states: INIT (show start screen, bird idle bob animation), READY (countdown 3-2-1 using requestAnimationFrame delta), PLAYING (physics active, pipe spawning), PAUSED (render dimmed overlay, stop physics), GAME_OVER (shake camera 10 frames, fade to red overlay 500ms), RESTART (reset bird position, clear pipes, restore score). Use Promises for state transitions and async asset loading.

**Procedural Generation:**
Spawn pipes every 90 frames (1.5 seconds at 60fps) with vertical offset randomized between -150 and +150 units, gap size 200 units, horizontal speed -3 units/frame. Implement object pooling with pre-allocated array of 10 pipe pairs, recycling offscreen pipes. Add difficulty scaling: increase pipe speed by 0.1 units/frame every 10 points (max speed: -6 units/frame), decrease gap size by 5 units every 15 points (min gap: 120 units).

**Progression Systems:**
Create unlockable bird skins stored in localStorage as JSON array: default (orange), bronze (10 points), silver (25 points), gold (50 points), diamond (100 points). Each skin has unique geometry shader for vertex displacement and material properties. Implement power-up system: shield (5-second invincibility, cyan glow), magnet (attract coins within 100 units), slow-motion (0.5x time scale for 3 seconds). Power-ups spawn randomly (15% chance per pipe pair) as rotating torus geometries.

**Mobile Optimization:**
Detect touch support using window.ontouchstart and bind touchstart/touchend events. Implement adaptive quality based on performance: monitor frame delta time, downgrade shadow resolution from 2048→1024→512 and disable bloom if FPS drops below 50 for 3 consecutive seconds. Use devicePixelRatio clamping (max: 2) to reduce render target size on high-DPI displays. Add passive event listeners and prevent default scrolling on game canvas.

**UI Framework:**
Build HUD using HTML overlays with CSS transforms (will-change: transform) for GPU acceleration. Score counter uses requestAnimationFrame for smooth counting animation (ease-out-cubic, duration: 300ms). Implement modal system with backdrop blur (backdrop-filter: blur(10px)), fade-in transitions (opacity + scale transform), and focus trap for accessibility. Settings panel includes range sliders for master volume, SFX volume, music volume (0-100), and radio buttons for quality presets (low/medium/high/ultra).

**Code Architecture:**
Structure as ES modules: Game.js (main loop, state management, RAF loop), Bird.js (extends THREE.Object3D, handles physics/animation), PipeManager.js (factory pattern for pipe generation, pooling), CameraController.js (smooth follow using lerp, shake using Perlin noise), AudioManager.js (singleton pattern, manages AudioContext lifecycle), UIManager.js (DOM manipulation, event delegation), SceneManager.js (Three.js scene setup, lighting, environment). Use Webpack for bundling with tree shaking and code splitting.

**Performance Targets:**
Maintain 60fps (16.67ms frame budget) on mid-range devices (5-year-old smartphone, integrated GPU). Limit draw calls to <50 per frame using geometry merging. Keep texture memory under 50MB using compressed formats (ASTC/ETC2 with fallback to PNG). Implement frustum culling for offscreen pipes and LOD system (3 detail levels based on distance). Use InstancedMesh for particle systems to batch draw calls.

**Build System:**
Provide package.json with dependencies: three@0.160.0, webpack@5.89.0, webpack-dev-server@4.15.0, babel@7.23.0, terser-webpack-plugin@5.3.9. Include npm scripts: "dev" (webpack-dev-server with hot reload), "build" (production bundle with minification and source maps), "lint" (ESLint with airbnb config), "test" (Jest unit tests for game logic). Configure webpack to output to dist/ with hashed filenames for cache busting.

**File Organization:**
```
/src
  /assets
    /models (GLTF bird models, pipe textures)
    /audio (MP3/OGG audio files)
    /textures (environment maps, particle sprites)
  /js
    /core (Game.js, SceneManager.js, CameraController.js)
    /entities (Bird.js, Pipe.js, PowerUp.js)
    /managers (AudioManager.js, UIManager.js, InputManager.js)
    /utils (MathUtils.js, PoolManager.js, StateMachine.js)
  /css (styles.css with CSS variables, media queries)
  index.html (canvas element, UI overlays, preload screen)
  main.js (entry point, initializes Game instance)
/dist (webpack output)
```

**Documentation Requirements:**
Include JSDoc comments for all classes/methods with @param, @returns, @example tags. Provide README.md with setup instructions (npm install, npm run dev), architecture overview diagram (ASCII or Mermaid), and configuration guide for tweaking physics constants. Add inline comments explaining complex algorithms (collision detection, camera interpolation, particle emission). Include performance profiling guide using Chrome DevTools Performance tab.

**Browser Compatibility:**
Target ES2020 syntax with Babel transpilation to ES5 for legacy support. Use feature detection for WebGL2 (fallback to WebGL1), AudioContext (fallback to legacy webkitAudioContext), and ResizeObserver (fallback to window.resize). Test on Chrome 100+, Firefox 100+, Safari 15+, Edge 100+, and mobile browsers (iOS Safari 15+, Chrome Android 100+).

**Deliverables:**
Complete source code with all assets embedded or externally linked, production webpack bundle (minified, gzipped <500KB), deployment guide for static hosting (Netlify/Vercel), and video demo recording showing gameplay at 60fps with all features enabled. Include unit tests for Bird physics, collision detection, pipe pooling, and score calculation with >80% code coverage.