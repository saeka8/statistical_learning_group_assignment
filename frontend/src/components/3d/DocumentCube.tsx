import { RoundedBox, Sparkles } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import { useRef } from 'react';
import { DoubleSide, type Group } from 'three';

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
    const z = Math.sin(t * 1.08) * (radius * 0.84) + depthOffset;
    const y = Math.sin(t * 1.7) * 0.48 + Math.cos(t * 0.85) * 0.08;

    groupRef.current.position.set(x, y, z);
    groupRef.current.lookAt(0, 0, 0);
    groupRef.current.rotation.z += 0.011;
  });

  return (
    <group ref={groupRef}>
      <RoundedBox args={[1.42, 1.9, 0.06]} radius={0.08} smoothness={4}>
        <meshStandardMaterial color={tint} roughness={0.18} metalness={0.08} />
      </RoundedBox>

      {[0.48, 0.18, -0.12, -0.42].map((y, index) => (
        <mesh key={index} position={[0, y, 0.038]}>
          <boxGeometry args={[index === 0 ? 0.82 : 1.02, 0.055, 0.01]} />
          <meshStandardMaterial color="#8f99a8" transparent opacity={0.38} />
        </mesh>
      ))}

      <mesh position={[0, 0.68, 0.039]}>
        <boxGeometry args={[0.66, 0.085, 0.01]} />
        <meshStandardMaterial color={accent} emissive={accent} emissiveIntensity={0.36} />
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
    const scale = 1 + Math.sin(t) * 0.12;
    haloRef.current.scale.setScalar(scale);
    haloRef.current.rotation.z = Math.sin(t * 0.36) * 0.2;
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
      scannerRef.current.rotation.y = t * 0.52;
      scannerRef.current.rotation.x = Math.sin(t * 0.56) * 0.18;
      scannerRef.current.rotation.z = Math.cos(t * 0.32) * 0.08;
      scannerRef.current.position.y = Math.sin(t * 0.82) * 0.14;
    }

    if (beamRef.current) {
      beamRef.current.scale.y = 0.92 + Math.sin(t * 1.9) * 0.2;
      beamRef.current.rotation.z = Math.sin(t * 0.72) * 0.12;
    }

    if (crystalRef.current) {
      crystalRef.current.rotation.y = t * 1.04;
      crystalRef.current.rotation.x = Math.sin(t * 0.74) * 0.34;
      crystalRef.current.rotation.z = Math.cos(t * 0.68) * 0.18;
      crystalRef.current.position.y = Math.sin(t * 1.24) * 0.08;
    }
  });

  return (
    <group ref={scannerRef}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.42, 0.14, 28, 120]} />
        <meshStandardMaterial
          color="#0f8ea1"
          emissive="#4ac8d8"
          emissiveIntensity={0.38}
          metalness={0.7}
          roughness={0.18}
        />
      </mesh>

      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.95, 0.05, 20, 100]} />
        <meshStandardMaterial color="#cf8c45" emissive="#cf8c45" emissiveIntensity={0.24} />
      </mesh>

      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.92, 0.92, 0.18, 72]} />
        <meshPhysicalMaterial
          color="#fff6ea"
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
        <meshBasicMaterial color="#ffd49c" transparent opacity={0.62} side={DoubleSide} />
      </mesh>

      <group ref={beamRef}>
        <mesh>
          <cylinderGeometry args={[0.05, 0.22, 3.5, 24, 1, true]} />
          <meshBasicMaterial color="#84effa" transparent opacity={0.18} />
        </mesh>
        <mesh position={[0, 1.12, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.18, 0.34, 40]} />
          <meshBasicMaterial color="#84effa" transparent opacity={0.54} side={DoubleSide} />
        </mesh>
      </group>

      <group ref={crystalRef}>
        <mesh>
          <octahedronGeometry args={[0.38, 0]} />
          <meshStandardMaterial
            color="#fff0d2"
            emissive="#d8934e"
            emissiveIntensity={0.44}
            metalness={0.28}
            roughness={0.14}
          />
        </mesh>
      </group>
    </group>
  );
}

export function DocumentCubeScene() {
  const rootRef = useRef<Group>(null);

  useFrame(({ clock }) => {
    if (!rootRef.current) return;

    const t = clock.getElapsedTime();
    const scale = 1.22 + Math.sin(t * 0.72) * 0.04;

    rootRef.current.rotation.y = Math.sin(t * 0.34) * 0.54;
    rootRef.current.rotation.x = -0.18 + Math.sin(t * 0.26) * 0.11;
    rootRef.current.rotation.z = Math.cos(t * 0.2) * 0.08;
    rootRef.current.position.y = Math.sin(t * 0.64) * 0.24;
    rootRef.current.scale.setScalar(scale);
  });

  return (
    <group ref={rootRef} position={[0, 0, 0]} scale={1.22}>
      <ambientLight intensity={0.52} />
      <spotLight
        position={[0, 6, 2.8]}
        angle={0.48}
        penumbra={1}
        intensity={56}
        color="#ffd49c"
      />
      <pointLight position={[2.8, 1.6, 3.1]} intensity={18} color="#73d8e5" />
      <pointLight position={[-2.8, -1.2, -2.4]} intensity={9} color="#cf8c45" />
      <pointLight position={[0, 2.4, -2.8]} intensity={7} color="#dceeff" />

      <mesh position={[0, -1.75, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.55, 3.1, 64]} />
        <meshBasicMaterial color="#84effa" transparent opacity={0.08} side={DoubleSide} />
      </mesh>

      <PulseHalo radius={1.86} color="#73d8e5" speed={1.34} phase={0} />
      <PulseHalo radius={2.18} color="#cf8c45" speed={1.04} phase={1.2} />
      <ScannerCore />

      <OrbitingSheet
        radius={2.55}
        angleOffset={0.2}
        speed={0.72}
        tint="#fff7ec"
        accent="#cf8c45"
      />
      <OrbitingSheet
        radius={2.2}
        angleOffset={2.2}
        speed={0.84}
        tint="#eefbfc"
        accent="#0f8ea1"
        depthOffset={0.1}
      />
      <OrbitingSheet
        radius={2.85}
        angleOffset={4.2}
        speed={0.66}
        tint="#f7efe4"
        accent="#234566"
        depthOffset={-0.18}
      />

      <Sparkles count={78} scale={[6.2, 4.8, 6.2]} size={2.2} speed={0.36} color="#ffd49c" />
      <Sparkles count={48} scale={[4.8, 3.4, 4.8]} size={3.1} speed={0.54} color="#73d8e5" />
    </group>
  );
}
