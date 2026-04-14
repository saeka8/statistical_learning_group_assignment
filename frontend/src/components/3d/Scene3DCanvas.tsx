import { Canvas } from '@react-three/fiber';
import { DocumentCubeScene } from './DocumentCube';

export function Scene3DCanvas() {
  return (
    <Canvas
      camera={{ position: [0, 0.15, 5.15], fov: 28 }}
      style={{ width: '100%', height: '100%' }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
    >
      <DocumentCubeScene />
    </Canvas>
  );
}
