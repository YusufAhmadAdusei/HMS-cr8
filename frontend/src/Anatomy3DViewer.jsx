import { Suspense, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { Html, Line, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { bodyCallouts, ValueLabel } from "./anatomyData";

const MODEL_URL = "/models/anatomy-female.glb";
const modelPreview = "/assets/3view_human_model_2.avif";

function ModelCallouts({ metrics }) {
  return bodyCallouts.filter((item) => item.key === "Solar8000/NIBP_SBP"
    ? metrics[item.key] || metrics["Solar8000/NIBP_DBP"]
    : metrics[item.key]).map((item) => <group key={item.key}>
      <Line points={[item.anchor3d, [(item.anchor3d[0] + item.label3d[0]) / 2, item.label3d[1], item.anchor3d[2]], item.label3d]} color="#8cebd6" lineWidth={1} transparent opacity={0.8} />
      <Html position={item.label3d} center distanceFactor={3.8} occlude>
        <ValueLabel item={item} metrics={metrics} className="body-callout-3d" />
      </Html>
    </group>);
}

function AnatomyModel({ metrics }) {
  const { scene } = useGLTF(MODEL_URL);
  const model = useMemo(() => {
    const root = scene.clone(true);
    const materials = {
      skin: new THREE.MeshPhysicalMaterial({ color: "#6fbdc9", roughness: 0.58, metalness: 0.02, transparent: true, opacity: 0.13, depthWrite: false, side: THREE.DoubleSide }),
      skeleton: new THREE.MeshStandardMaterial({ color: "#c1d5d1", roughness: 0.75, transparent: true, opacity: 0.46, side: THREE.DoubleSide }),
      muscles: new THREE.MeshStandardMaterial({ color: "#8a5963", roughness: 0.82, side: THREE.DoubleSide }),
      organs: new THREE.MeshStandardMaterial({ color: "#c97982", roughness: 0.62, side: THREE.DoubleSide }),
      vessels: new THREE.MeshStandardMaterial({ color: "#b84f5c", roughness: 0.62, side: THREE.DoubleSide }),
      nerves: new THREE.MeshStandardMaterial({ color: "#e0b980", roughness: 0.7, side: THREE.DoubleSide }),
    };
    for (const [system, material] of Object.entries(materials)) {
      const layer = root.getObjectByName(system);
      if (!layer) continue;
      if (system === "muscles") layer.visible = false;
      layer.traverse((node) => {
        if (node.isMesh) {
          node.material = material;
          node.frustumCulled = false;
        }
      });
    }
    return root;
  }, [scene]);

  return <>
    <ambientLight intensity={1.05} />
    <directionalLight position={[2, 3, 4]} intensity={2.1} color="#d5ffff" />
    <directionalLight position={[-2, 1, -2]} intensity={1.15} color="#ff8198" />
    <primitive object={model} />
    <ModelCallouts metrics={metrics} />
    <OrbitControls target={[0, 1.0, 0]} enablePan={false} minDistance={2.2} maxDistance={5} minPolarAngle={0.25} maxPolarAngle={2.85} />
  </>;
}

function ModelLoading() {
  return <Html center><div className="anatomy-loading"><img src={modelPreview} alt="Anatomical model preview"/><span>Loading 3D anatomy…</span></div></Html>;
}

export default function Anatomy3DViewer({ metrics }) {
  return <Canvas className="anatomy-canvas" dpr={[1, 1.4]} camera={{ position: [0, 1.12, 3.8], fov: 34 }} gl={{ alpha: true, antialias: true, powerPreference: "low-power" }}>
    <Suspense fallback={<ModelLoading />}><AnatomyModel metrics={metrics} /></Suspense>
  </Canvas>;
}
