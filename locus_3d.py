import os
import json
import tempfile
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot, QUrl, Qt
from basalt_node import BasaltTree

class LocusBridge(QObject):
    """Python <-> JS Communication bridge"""
    def __init__(self, tree: BasaltTree, parent=None):
        super().__init__(parent)
        self.tree = tree

    @pyqtSlot(str)
    def save_camera_state(self, state_json):
        try:
            data = json.loads(state_json)
            self.tree.locus_cam_pos = data.get('pos', self.tree.locus_cam_pos)
            self.tree.locus_cam_rot = data.get('rot', self.tree.locus_cam_rot)
            print(f"[Locus] Location saved: {self.tree.title}")
        except Exception as e:
            print(f"[Locus] Failed to save location: {e}")

class Locus3DDialog(QDialog):
    def __init__(self, tree: BasaltTree, parent=None):
        super().__init__(parent)
        self.tree = tree
        self.setWindowTitle(f"🏰 Locus: {tree.title}")
        self.resize(1280, 720)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = QWebEngineView()
        layout.addWidget(self.view)
        
        self.bridge = LocusBridge(tree, self)
        self.channel = QWebChannel(self.view.page())
        self.channel.registerObject('bridge', self.bridge)
        self.view.page().setWebChannel(self.channel)
        
        self._load_scene()

    def _load_scene(self):
        nodes_data = []
        for n in self.tree.nodes.values():
            nodes_data.append({
                "id": n.id,
                "title": n.title,
                "note": n.note or "",
                "x": n.x * 0.25, 
                "y": n.y * 0.25,
                "children": n.children
            })
        
        tree_json = json.dumps({
            "nodes": nodes_data,
            "root_id": self.tree.root_id,
            "cam_pos": self.tree.locus_cam_pos,
            "cam_rot": self.tree.locus_cam_rot
        })
        
        html_content = self._get_html_template().replace("/*TREE_DATA_PLACEHOLDER*/", tree_json)
        
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "basalt_locus.html")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        self.view.setUrl(QUrl.fromLocalFile(temp_path))

    def _get_html_template(self):
        return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src * 'unsafe-inline' 'unsafe-eval'; script-src * 'unsafe-inline' 'unsafe-eval';">
<style>
body { margin: 0; overflow: hidden; background: #050510; font-family: sans-serif; }
canvas { display: block; }
#ui-overlay {
    position: absolute; top: 0; left: 0; width: 100%; pointer-events: none;
    text-align: center; color: #10b981; font-size: 14px; padding: 10px;
    text-shadow: 0 0 5px #000; background: rgba(0,0,0,0.5);
    box-sizing: border-box;
}
</style>
</head>
<body>
<div id="ui-overlay">🏰 Locus Memory Palace | Зажми ЛКМ + двигай мышь, чтобы смотреть | WASD для движения</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
let scene, camera, renderer;
let moveForward = false, moveBackward = false, moveLeft = false, moveRight = false;
let isLooking = false;
let euler = new THREE.Euler(0, 0, 0, 'YXZ');
let bridge = null;
const treeData = /*TREE_DATA_PLACEHOLDER*/;

const collisionRooms = [];
const collisionCorridors = [];

if (typeof QWebChannel !== 'undefined') {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        bridge = channel.objects.bridge;
    });
}

function init() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x050510);
    scene.fog = new THREE.FogExp2(0x050510, 0.012);

    camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 2000);
    
    scene.add(new THREE.AmbientLight(0x404040, 0.8));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
    dirLight.position.set(50, 100, 50);
    scene.add(dirLight);

    buildPalace();

    let startPos = new THREE.Vector3(0, 2, 0);
    if (treeData.root_id) {
        let rootNode = treeData.nodes.find(n => n.id === treeData.root_id);
        if (rootNode) startPos.set(rootNode.x, 2, rootNode.y);
    }
    camera.position.copy(startPos);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    document.body.appendChild(renderer.domElement);

    document.addEventListener('mousedown', (e) => {
        if (e.button === 0) isLooking = true;
    });
    
    document.addEventListener('mouseup', (e) => {
        if (e.button === 0) {
            isLooking = false;
            if (bridge) {
                bridge.save_camera_state(JSON.stringify({
                    pos: camera.position.toArray(),
                    rot: euler.toArray()
                }));
            }
        }
    });

    document.addEventListener('mousemove', (event) => {
        if (!isLooking) return;
        const movementX = event.movementX || 0;
        const movementY = event.movementY || 0;

        euler.setFromQuaternion(camera.quaternion);
        euler.y -= movementX * 0.002;
        euler.x -= movementY * 0.002;
        euler.x = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, euler.x));
        camera.quaternion.setFromEuler(euler);
    });

    document.addEventListener('keydown', (event) => {
        switch (event.code) {
            case 'KeyW': moveForward = true; break;
            case 'KeyS': moveBackward = true; break;
            case 'KeyA': moveLeft = true; break;
            case 'KeyD': moveRight = true; break;
        }
    });

    document.addEventListener('keyup', (event) => {
        switch (event.code) {
            case 'KeyW': moveForward = false; break;
            case 'KeyS': moveBackward = false; break;
            case 'KeyA': moveLeft = false; break;
            case 'KeyD': moveRight = false; break;
        }
    });

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    window.addEventListener('beforeunload', () => {
        if (bridge) {
            bridge.save_camera_state(JSON.stringify({
                pos: camera.position.toArray(),
                rot: euler.toArray()
            }));
        }
    });

    animate();
}

function isValidPosition(x, z) {
    for (let i = 0; i < collisionRooms.length; i++) {
        const r = collisionRooms[i];
        const dx = x - r.x;
        const dz = z - r.z;
        if (dx*dx + dz*dz < r.r * r.r) return true;
    }
    for (let i = 0; i < collisionCorridors.length; i++) {
        const c = collisionCorridors[i];
        const dx = c.x2 - c.x1;
        const dz = c.z2 - c.z1;
        const lenSq = dx*dx + dz*dz;
        if (lenSq === 0) continue;
        
        let t = ((x - c.x1) * dx + (z - c.z1) * dz) / lenSq;
        t = Math.max(0, Math.min(1, t));
        
        const projX = c.x1 + t * dx;
        const projZ = c.z1 + t * dz;
        const distSq = (x - projX)**2 + (z - projZ)**2;
        
        if (distSq < c.w * c.w) return true;
    }
    return false;
}

function buildPalace() {
    const nodeMap = {};
    treeData.nodes.forEach(n => nodeMap[n.id] = n);

    // 1. Построение карты родителей для ориентации панелей
    const parentMap = {};
    treeData.nodes.forEach(n => {
        n.children.forEach(childId => {
            parentMap[childId] = n.id;
        });
    });

    // 2. Предварительный расчет радиусов для всех узлов (чтобы избежать пересечений)
    const nodeRadii = {};
    treeData.nodes.forEach(n => {
        let minDistToChild = Infinity;
        n.children.forEach(childId => {
            const child = nodeMap[childId];
            if (child) {
                const dist = Math.hypot(child.x - n.x, child.y - n.y);
                if (dist < minDistToChild) minDistToChild = dist;
            }
        });
        
        const baseRadius = 8;
        const spacing = 6; // Минимальный зазор между выходами на окружности
        const requiredRadius = (n.children.length * spacing) / (2 * Math.PI);
        
        // Радиус не может превышать половину расстояния до ближайшего ребенка минус буфер для коридора (3 ед.)
        const maxAllowedRadius = minDistToChild === Infinity ? 20 : Math.max(baseRadius, (minDistToChild / 2) - 3);
        
        nodeRadii[n.id] = Math.max(baseRadius, Math.min(requiredRadius, maxAllowedRadius));
    });

    const floorMat = new THREE.MeshStandardMaterial({ color: 0x1a202c, emissive: 0x3772d6, emissiveIntensity: 0.3 });
    const wallMat = new THREE.MeshStandardMaterial({ 
        color: 0x3772d6, transparent: true, opacity: 0.15, 
        side: THREE.DoubleSide, emissive: 0x3772d6, emissiveIntensity: 0.5,
        depthWrite: false
    });
    const corridorFloorMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, emissive: 0x10b981, emissiveIntensity: 0.2 });
    const corridorWallMat = new THREE.MeshStandardMaterial({ 
        color: 0x10b981, transparent: true, opacity: 0.1, 
        side: THREE.DoubleSide, depthWrite: false 
    });

    treeData.nodes.forEach(node => {
        const pos = new THREE.Vector3(node.x, 0, node.y);
        const roomRadius = nodeRadii[node.id];

        collisionRooms.push({ x: pos.x, z: pos.z, r: roomRadius });

        const floorGeo = new THREE.CylinderGeometry(roomRadius, roomRadius, 0.5, 32);
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.position.copy(pos);
        floor.position.y = -0.25;
        scene.add(floor);

        const gridHelper = new THREE.GridHelper(roomRadius * 2, 16, 0x3772d6, 0x1e3a8a);
        gridHelper.position.copy(pos);
        gridHelper.position.y = 0.01;
        scene.add(gridHelper);

        const wallGeo = new THREE.CylinderGeometry(roomRadius, roomRadius, 6, 32, 1, true);
        const wall = new THREE.Mesh(wallGeo, wallMat);
        wall.position.copy(pos);
        wall.position.y = 3;
        wall.renderOrder = 1;
        scene.add(wall);

        // 3. Создание и ориентация голографической панели
        const holoPanel = createHoloPanel(node.title, node.note);
        holoPanel.position.set(pos.x, 3, pos.z);
        
        let targetPos = null;
        if (node.id === treeData.root_id) {
            // Корневой узел: смотрим в сторону, противоположную среднему вектору на детей
            if (node.children.length > 0) {
                let avgX = 0, avgY = 0;
                node.children.forEach(childId => {
                    const child = nodeMap[childId];
                    avgX += (child.x - node.x);
                    avgY += (child.y - node.y);
                });
                avgX /= node.children.length;
                avgY /= node.children.length;
                // Инвертируем средний вектор, чтобы смотреть "перед" проходами
                targetPos = new THREE.Vector3(node.x - avgX, 3, node.y - avgY);
            } else {
                targetPos = new THREE.Vector3(node.x, 3, node.y + 10); // Фоллбэк
            }
        } else {
            // Обычный узел: смотрим строго на родителя
            const parentId = parentMap[node.id];
            const parent = nodeMap[parentId];
            if (parent) {
                targetPos = new THREE.Vector3(parent.x, 3, parent.y);
            } else {
                targetPos = new THREE.Vector3(node.x, 3, node.y + 10);
            }
        }
        
        if (targetPos) {
            holoPanel.lookAt(targetPos);
        }
        scene.add(holoPanel);

        // 4. Коридоры, начинающиеся и заканчивающиеся на границах комнат
        node.children.forEach(childId => {
            const child = nodeMap[childId];
            if (!child) return;

            const parentPos = new THREE.Vector3(node.x, 0, node.y);
            const childPos = new THREE.Vector3(child.x, 0, child.y);
            const dir = new THREE.Vector3().subVectors(childPos, parentPos);
            const dist = dir.length();
            if (dist < 1) return; 

            dir.normalize();

            const r1 = nodeRadii[node.id];
            const r2 = nodeRadii[child.id];

            const startPos = parentPos.clone().add(dir.clone().multiplyScalar(r1));
            const endPos = childPos.clone().sub(dir.clone().multiplyScalar(r2));
            
            const length = startPos.distanceTo(endPos);
            if (length < 0.5) return; // Защита от слишком коротких коридоров

            const mid = new THREE.Vector3().addVectors(startPos, endPos).multiplyScalar(0.5);
            const angle = Math.atan2(dir.x, dir.z);


            collisionCorridors.push({
                x1: startPos.x, z1: startPos.z,
                x2: endPos.x, z2: endPos.z,
                w: 2.0 
            });

            const cFloorGeo = new THREE.BoxGeometry(4, 0.5, length);
            const cFloor = new THREE.Mesh(cFloorGeo, corridorFloorMat);
            cFloor.position.set(mid.x, -0.25, mid.z);
            cFloor.rotation.y = angle;
            scene.add(cFloor);

            const cWallGeo = new THREE.BoxGeometry(0.2, 6, length);
            const rightVec = new THREE.Vector3(Math.cos(angle), 0, -Math.sin(angle));
            
            const cWallL = new THREE.Mesh(cWallGeo, corridorWallMat);
            cWallL.position.set(mid.x, 3, mid.z);
            cWallL.rotation.y = angle;
            cWallL.position.add(rightVec.clone().multiplyScalar(2));
            cWallL.renderOrder = 1;
            scene.add(cWallL);

            const cWallR = new THREE.Mesh(cWallGeo, corridorWallMat);
            cWallR.position.set(mid.x, 3, mid.z);
            cWallR.rotation.y = angle;
            cWallR.position.add(rightVec.clone().multiplyScalar(-2));
            cWallR.renderOrder = 1;
            scene.add(cWallR);

            const cCeilGeo = new THREE.BoxGeometry(4, 0.2, length);
            const cCeil = new THREE.Mesh(cCeilGeo, corridorWallMat);
            cCeil.position.set(mid.x, 6, mid.z);
            cCeil.rotation.y = angle;
            cCeil.renderOrder = 1;
            scene.add(cCeil);
        });
    });
}

function createHoloPanel(title, note) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 512; canvas.height = 512;
    
    ctx.fillStyle = 'rgba(10, 15, 30, 0.85)';
    ctx.fillRect(0, 0, 512, 512);
    
    ctx.strokeStyle = '#3772d6'; ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, 508, 508);
    
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 36px Arial';
    ctx.textAlign = 'center';
    let displayTitle = title.length > 30 ? title.substring(0, 30) + '...' : title;
    ctx.fillText(displayTitle, 256, 60);
    
    ctx.fillStyle = '#cbd5e1';
    ctx.font = '22px Arial';
    ctx.textAlign = 'left';
    wrapText(ctx, note, 30, 120, 450, 30);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    
    const material = new THREE.MeshBasicMaterial({ 
        map: texture, 
        transparent: true, 
        side: THREE.DoubleSide, 
        depthWrite: false
    });
    const geo = new THREE.PlaneGeometry(8, 8);
    const mesh = new THREE.Mesh(geo, material);
    mesh.renderOrder = 2;
    return mesh;
}

function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
    if(!text) return;
    let words = text.split(' ');
    let line = '';
    for(let n = 0; n < words.length; n++) {
        let testLine = line + words[n] + ' ';
        if (ctx.measureText(testLine).width > maxWidth && n > 0) {
            ctx.fillText(line, x, y);
            line = words[n] + ' ';
            y += lineHeight;
            if(y > 480) break;
        } else {
            line = testLine;
        }
    }
    ctx.fillText(line, x, y);
}

function animate() {
    requestAnimationFrame(animate);
    const delta = 0.05;
    const speed = 6.0;
    const moveStep = speed * delta;
    
    const camDir = new THREE.Vector3();
    camera.getWorldDirection(camDir);
    camDir.y = 0; camDir.normalize();
    const camRight = new THREE.Vector3().crossVectors(camDir, new THREE.Vector3(0, 1, 0)).normalize();

    let newX = camera.position.x;
    let newZ = camera.position.z;

    if (moveForward) { newX += camDir.x * moveStep; newZ += camDir.z * moveStep; }
    if (moveBackward) { newX -= camDir.x * moveStep; newZ -= camDir.z * moveStep; }
    if (moveLeft) { newX -= camRight.x * moveStep; newZ -= camRight.z * moveStep; }
    if (moveRight) { newX += camRight.x * moveStep; newZ += camRight.z * moveStep; }

    if (isValidPosition(newX, newZ)) {
        camera.position.x = newX;
        camera.position.z = newZ;
    } else {
        if (isValidPosition(newX, camera.position.z)) {
            camera.position.x = newX;
        } else if (isValidPosition(camera.position.x, newZ)) {
            camera.position.z = newZ;
        }
    }

    camera.position.y = 2.0;
    renderer.render(scene, camera);
}

init();
</script>
</body>
</html>
"""

    def closeEvent(self, event):
        if self.bridge and self.view:
            try:
                self.view.page().runJavaScript("""
                    if (typeof bridge !== 'undefined' && bridge) {
                        bridge.save_camera_state(JSON.stringify({
                            pos: camera.position.toArray(),
                            rot: euler.toArray()
                        }));
                    }
                """)
            except Exception:
                pass
        super().closeEvent(event)