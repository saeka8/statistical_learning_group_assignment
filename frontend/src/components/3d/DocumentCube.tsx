import { RoundedBox, Sparkles } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import { DoubleSide, Group } from 'three';

function OrbitingSheet({
  radius,
  angleOffset,
  speed,
  tint,
  accent,
  depthOffset = 0,
}: {
  radius: number;
  angleOffset: number;
  speed: number;
  tint: string;
  accent: string;
  depthOffset?: number;
}) {
  const groupRef = useRef<Group>(null);

  useFrame(({ clock }) => {
    if (!groupRef.current) return;

    const t = clock.getElapsedTime() * speed + angleOffset;
    const x = Math.cos(t) * radius;
    const z = Math.sin(t) * (radius * 0.72) + depthOffset;
    const y = Math.sin(t * 1.4) * 0.34;

    groupRef.current.position.set(x, y, z);
    groupRef.current.lookAt(0, 0, 0);
    groupRef.current.rotation.z += 0.007;
  });

  return (
    <group ref={groupRef}>
      <RoundedBox args={[1.42, 1.9, 0.06]} radius={0.08} smoothness={4}>
        <meshStandardMaterial color={tint} roughness={0.2} metalness={0.06} />
      </RoundedBox>

      {[0.48, 0.18, -0.12, -0.42].map((y, index) => (
        <mesh key={index} position={[0, y, 0.038]}>
          <boxGeometry args={[index === 0 ? 0.82 : 1.02, 0.055, 0.01]} />
          <meshStandardMaterial color="#8f99a8" transparent opacity={0.38} />
        </mesh>
      ))}

      <mesh position={[0, 0.68, 0.039]}>
        <boxGeometry args={[0.66, 0.085, 0.01]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.25} />
      </mesh>

      <mesh position={[0.34, -0.72, 0.04]}>
        <boxGeometry args={[0.34, 0.11, 0.01]} />
        <meshStandardMaterial color="#e6edf5" />
      </mesh>
    </group>
  );
}

function PulseHalo({
  radius,
  color,
  speed,
  phase,
}: {
  radius: number;
  color: string;
  speed: number;
  phase: number;
}) {
  const haloRef = useRef<Group>(null);

  useFrame(({ clock }) => {
    if (!haloRef.current) return;
    const t = clock.getElapsedTime() * speed + phase;
    const scale = 1 + Math.sin(t) * 0.08;
    haloRef.current.scale.setScalar(scale);
  });

  return (
    <group ref={haloRef} rotation={[Math.PI / 2, 0, 0]}>
      <mesh>
        <torusGeometry args={[radius, 0.024, 16, 120]} />
        <meshBasicMaterial color={color} transparent opacity={0.34} />
      </mesh>
    </group>
  );
}

function ScannerCore() {
  const scannerRef = useRef<Group>(null);
  const beamRef = useRef<Group>(null);
  const crystalRef = useRef<Group>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    if (scannerRef.current) {
      scannerRef.current.rotation.y = t * 0.34;
      scannerRef.current.rotation.x = Math.sin(t * 0.4) * 0.12;
      scannerRef.current.position.y = Math.sin(t * 0.6) * 0.08;
    }

    if (beamRef.current) {
      beamRef.current.scale.y = 0.9 + Math.sin(t * 1.7) * 0.12;
    }

    if (crystalRef.current) {
      crystalRef.current.rotation.y = t * 0.7;
      crystalRef.current.rotation.x = Math.sin(t * 0.55) * 0.3;
    }
  });

  return (
    <group ref={scannerRef}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.42, 0.14, 28, 120]} />
        <meshStandardMaterial
          color="#20b6d9"
          emissive="#20b6d9"
          emissiveIntensity={0.28}
          metalness={0.7}
          roughness={0.18}
        />
      </mesh>

      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.95, 0.05, 20, 100]} />
        <meshStandardMaterial color="#efaa4f" emissive="#efaa4f" emissiveIntensity={0.16} />
      </mesh>

      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.92, 0.92, 0.18, 72]} />
        <meshPhysicalMaterial
          color="#fffdf8"
          roughness={0.06}
          metalness={0.04}
          transmission={0.92}
          thickness={0.7}
          transparent
          opacity={0.94}
        />
      </mesh>

      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.44, 0.72, 64]} />
        <meshBasicMaterial color="#ffe0ad" transparent opacity={0.58} side={DoubleSide} />
      </mesh>

      <group ref={beamRef}>
        <mesh>
          <cylinderGeometry args={[0.05, 0.22, 3.5, 24, 1, true]} />
          <meshBasicMaterial color="#8cecff" transparent opacity={0.16} />
        </mesh>
        <mesh position={[0, 1.12, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.18, 0.34, 40]} />
          <meshBasicMaterial color="#8cecff" transparent opacity={0.52} side={DoubleSide} />
        </mesh>
      </group>

      <group ref={crystalRef}>
        <mesh>
          <octahedronGeometry args={[0.38, 0]} />
          <meshStandardMaterial
            color="#fff0d2"
            emissive="#efaa4f"
            emissiveIntensity={0.34}
            metalness={0.28}
            roughness={0.14}
          />
        </mesh>
      </group>
    </group>
  );
}

export function DocumentCubeScene() {
  return (
    <group position={[0, 0, 0]} scale={1.22}>
      <ambientLight intensity={0.42} />
      <spotLight
        position={[0, 6, 2]}
        angle={0.42}
        penumbra={1}
        intensity={42}
        color="#ffe0ad"
      />
      <pointLight position={[2.5, 1.5, 3]} intensity={14} color="#7be1f6" />
      <pointLight position={[-2.8, -1.2, -2]} intensity={7} color="#efaa4f" />

      <mesh position={[0, -1.75, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.55, 3.1, 64]} />
        <meshBasicMaterial color="#8cecff" transparent opacity={0.08} side={DoubleSide} />
      </mesh>

      <PulseHalo radius={1.86} color="#7be1f6" speed={1.2} phase={0} />
      <PulseHalo radius={2.18} color="#efaa4f" speed={0.9} phase={1.2} />
      <ScannerCore />

      <OrbitingSheet
        radius={2.55}
        angleOffset={0.2}
        speed={0.54}
        tint="#fff8ee"
        accent="#efaa4f"
      />
      <OrbitingSheet
        radius={2.2}
        angleOffset={2.2}
        speed={0.62}
        tint="#f4fbff"
        accent="#20b6d9"
        depthOffset={0.1}
      />
      <OrbitingSheet
        radius={2.85}
        angleOffset={4.2}
        speed={0.47}
        tint="#f6f1ff"
        accent="#0d5fc9"
        depthOffset={-0.18}
      />

      <Sparkles count={55} scale={[6.2, 4.8, 6.2]} size={2.1} speed={0.28} color="#ffe0ad" />
      <Sparkles count={36} scale={[4.6, 3.2, 4.6]} size={2.8} speed={0.42} color="#7be1f6" />
    </group>
  );
}
