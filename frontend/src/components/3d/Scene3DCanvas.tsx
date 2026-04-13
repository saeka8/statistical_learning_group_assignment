import { OrbitControls } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import { DocumentCubeScene } from './DocumentCube';

export function Scene3DCanvas() {
  return (
    <Canvas
      camera={{ position: [0, 0.1, 5.4], fov: 33 }}
      style={{ width: '100%', height: '100%' }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true }}
    >
      <DocumentCubeScene />
      <OrbitControls
        enableZoom={false}
        enablePan={false}
        autoRotate={false}
        maxPolarAngle={Math.PI / 1.8}
        minPolarAngle={Math.PI / 3}
      />
    </Canvas>
  );
}
