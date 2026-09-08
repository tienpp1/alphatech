/**
 * ============================================================================
 * KINETIC DUAL-CORE 3D ENGINE (THREE.JS)
 * Architectural Visualization for ABC Tech Store & XYZ IT Technical Services
 * Standardized via UI/UX Pro Max Best Practices
 * ============================================================================
 */

(function () {
    'use strict';

    // Wait until DOM and THREE library are loaded
    function initKineticHero() {
        const container = document.getElementById('three-canvas-container');
        if (!container) return;

        // Check if THREE is defined
        if (typeof THREE === 'undefined') {
            console.warn('[ThreeEngine] Three.js not loaded. Falling back to ambient background.');
            return;
        }

        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        // 1. Scene & Camera Setup
        const scene = new THREE.Scene();
        scene.fog = new THREE.FogExp2(0x080b0e, 0.04);

        const width = container.clientWidth || 540;
        const height = container.clientHeight || 400;

        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
        camera.position.set(0, 0.4, 9.2);

        // 2. High-Performance Renderer
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance',
        });
        renderer.setSize(width, height);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.2;

        renderer.domElement.setAttribute('role', 'img');
        renderer.domElement.setAttribute(
            'aria-label',
            'Mô hình 3D tương tác kiến trúc hệ sinh thái công nghệ ABC Tech & XYZ IT Services'
        );
        container.appendChild(renderer.domElement);

        // 3. Lighting Setup
        const ambientLight = new THREE.AmbientLight(0x11161b, 2.2);
        scene.add(ambientLight);

        // Key light (Cyber Sky Blue)
        const keyLight = new THREE.PointLight(0x38bdf8, 4.2, 30);
        keyLight.position.set(6, 5, 7);
        scene.add(keyLight);

        // Rim light (Cyber Amber Lamp)
        const rimLight = new THREE.PointLight(0xffb03a, 3.8, 30);
        rimLight.position.set(-6, -4, 5);
        scene.add(rimLight);

        // Center glow point (Cyber Cyan Glow)
        const coreLight = new THREE.PointLight(0x00f0ff, 3.0, 14);
        coreLight.position.set(0, 0, 0);
        scene.add(coreLight);

        // 4. Kinetic Dual-Core Group
        const kineticGroup = new THREE.Group();
        scene.add(kineticGroup);

        // --- Domain A: ABC Tech Hardware Core (Inner Precision Icosahedron) ---
        const coreGeometry = new THREE.IcosahedronGeometry(1.9, 1);
        const coreMaterial = new THREE.MeshPhysicalMaterial({
            color: 0x0284c7,
            emissive: 0x082f49,
            roughness: 0.12,
            metalness: 0.88,
            clearcoat: 1.0,
            clearcoatRoughness: 0.08,
            wireframe: false,
            transparent: true,
            opacity: 0.85,
        });
        const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
        kineticGroup.add(coreMesh);

        // Wireframe Lattice Layer
        const wireGeometry = new THREE.IcosahedronGeometry(1.96, 1);
        const wireMaterial = new THREE.MeshBasicMaterial({
            color: 0x38bdf8,
            wireframe: true,
            transparent: true,
            opacity: 0.45,
        });
        const wireMesh = new THREE.Mesh(wireGeometry, wireMaterial);
        kineticGroup.add(wireMesh);

        // Vertex Nodes (Glowing Data Points)
        const nodeGeometry = new THREE.IcosahedronGeometry(1.96, 1);
        const nodePositions = nodeGeometry.attributes.position;
        const ptsGeometry = new THREE.BufferGeometry();
        ptsGeometry.setAttribute('position', nodePositions);
        const ptsMaterial = new THREE.PointsMaterial({
            color: 0x00f0ff,
            size: 0.14,
            transparent: true,
            opacity: 0.95,
        });
        const nodePoints = new THREE.Points(ptsGeometry, ptsMaterial);
        kineticGroup.add(nodePoints);

        // --- Domain B: XYZ IT Infrastructure (Concentric Orbital Rings) ---
        const ringsGroup = new THREE.Group();
        kineticGroup.add(ringsGroup);

        // Orbital Ring 1 (Data Bus - Sky Blue)
        const ring1Geo = new THREE.TorusGeometry(3.1, 0.03, 16, 120);
        const ring1Mat = new THREE.MeshStandardMaterial({
            color: 0x38bdf8,
            emissive: 0x0369a1,
            roughness: 0.25,
            metalness: 0.85,
        });
        const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
        ring1.rotation.x = Math.PI * 0.35;
        ring1.rotation.y = Math.PI * 0.15;
        ringsGroup.add(ring1);

        // Orbital Ring 2 (Perimeter Bus - Amber Gold)
        const ring2Geo = new THREE.TorusGeometry(3.9, 0.025, 16, 140);
        const ring2Mat = new THREE.MeshStandardMaterial({
            color: 0xffb03a,
            emissive: 0xd97706,
            roughness: 0.3,
            metalness: 0.8,
        });
        const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
        ring2.rotation.x = -Math.PI * 0.28;
        ring2.rotation.z = Math.PI * 0.22;
        ringsGroup.add(ring2);

        // Satellite Node Cluster (IT Server / DB units)
        const satellites = [];
        const satCount = 4;
        const satGeo = new THREE.BoxGeometry(0.22, 0.22, 0.22);
        const satMat = new THREE.MeshStandardMaterial({
            color: 0x00f0ff,
            emissive: 0x0284c7,
            roughness: 0.2,
            metalness: 0.9,
        });

        for (let i = 0; i < satCount; i++) {
            const sat = new THREE.Mesh(satGeo, satMat);
            ringsGroup.add(sat);
            satellites.push({
                mesh: sat,
                radius: 3.1,
                angle: (i / satCount) * Math.PI * 2,
                speed: 0.008 + i * 0.003,
            });
        }

        // --- Domain C: Ambient Particle Field ---
        const particleCount = 160;
        const particleGeo = new THREE.BufferGeometry();
        const particlePositions = new Float32Array(particleCount * 3);

        for (let i = 0; i < particleCount * 3; i += 3) {
            particlePositions[i] = (Math.random() - 0.5) * 15;
            particlePositions[i + 1] = (Math.random() - 0.5) * 11;
            particlePositions[i + 2] = (Math.random() - 0.5) * 11;
        }
        particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
        const particleMat = new THREE.PointsMaterial({
            color: 0x38bdf8,
            size: 0.07,
            transparent: true,
            opacity: 0.65,
        });
        const particleField = new THREE.Points(particleGeo, particleMat);
        scene.add(particleField);

        // 5. Shared Raycasting & Input Handling
        const mouse = new THREE.Vector2(0, 0);
        const targetRotation = new THREE.Vector2(0, 0);
        let currentMode = 'all'; // 'all', 'retail', 'services'

        function onPointerMove(e) {
            const rect = container.getBoundingClientRect();
            const clientX = e.clientX || (e.touches && e.touches[0].clientX) || 0;
            const clientY = e.clientY || (e.touches && e.touches[0].clientY) || 0;

            mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;

            targetRotation.x = mouse.y * 0.4;
            targetRotation.y = mouse.x * 0.6;
        }

        container.addEventListener('pointermove', onPointerMove, { passive: true });
        container.addEventListener('touchmove', onPointerMove, { passive: true });

        // 6. Viewport Mode Switcher
        window.switchHeroSceneMode = function (mode) {
            currentMode = mode;
            const statusEl = document.getElementById('stage-status-text');

            // Update UI buttons
            document.querySelectorAll('.stage-pill-btn').forEach(function (btn) {
                btn.classList.toggle('active', btn.getAttribute('data-mode') === mode);
            });

            if (mode === 'retail') {
                // Focus on ABC Tech Hardware Core
                keyLight.color.setHex(0x38bdf8);
                keyLight.intensity = 5.0;
                rimLight.intensity = 1.2;
                coreMaterial.color.setHex(0x0284c7);
                coreMaterial.opacity = 0.95;
                ring1Mat.opacity = 0.35;
                ring2Mat.opacity = 0.2;
                if (statusEl) statusEl.textContent = 'MODE: ABC TECH HARDWARE HUB';
            } else if (mode === 'services') {
                // Focus on XYZ IT Infrastructure
                keyLight.intensity = 1.2;
                rimLight.color.setHex(0xffb03a);
                rimLight.intensity = 5.0;
                coreMaterial.color.setHex(0x082f49);
                coreMaterial.opacity = 0.4;
                ring1Mat.opacity = 0.95;
                ring2Mat.opacity = 0.95;
                if (statusEl) statusEl.textContent = 'MODE: XYZ IT INFRASTRUCTURE';
            } else {
                // All Ecosystem
                keyLight.color.setHex(0x38bdf8);
                keyLight.intensity = 4.2;
                rimLight.color.setHex(0xffb03a);
                rimLight.intensity = 3.8;
                coreMaterial.color.setHex(0x0284c7);
                coreMaterial.opacity = 0.85;
                ring1Mat.opacity = 0.8;
                ring2Mat.opacity = 0.8;
                if (statusEl) statusEl.textContent = 'MODE: COMBINED DUAL-ECOSYSTEM';
            }
        };

        // 7. Responsive Resizing
        function onResize() {
            if (!container) return;
            const newW = container.clientWidth;
            const newH = container.clientHeight;
            if (newW > 0 && newH > 0) {
                camera.aspect = newW / newH;
                camera.updateProjectionMatrix();
                renderer.setSize(newW, newH);
            }
        }

        const resizeObserver = new ResizeObserver(function () {
            onResize();
        });
        resizeObserver.observe(container);

        // 8. Animation Render Loop (Using renderer.setAnimationLoop)
        const clock = new THREE.Clock();

        function animate() {
            const delta = clock.getDelta();
            const time = clock.getElapsedTime();

            if (!prefersReducedMotion) {
                // Subtle core auto-rotation
                coreMesh.rotation.y += 0.003;
                coreMesh.rotation.x += 0.0015;
                wireMesh.rotation.y += 0.003;
                wireMesh.rotation.x += 0.0015;
                nodePoints.rotation.y += 0.003;
                nodePoints.rotation.x += 0.0015;

                // Orbiting rings rotation
                ring1.rotation.z += 0.004;
                ring2.rotation.y += 0.003;

                // Satellites motion along orbits
                satellites.forEach(function (sat) {
                    sat.angle += sat.speed;
                    sat.mesh.position.x = Math.cos(sat.angle) * sat.radius;
                    sat.mesh.position.y = Math.sin(sat.angle) * Math.cos(Math.PI * 0.35) * sat.radius;
                    sat.mesh.position.z = Math.sin(sat.angle) * Math.sin(Math.PI * 0.35) * sat.radius;
                    sat.mesh.rotation.x += 0.02;
                    sat.mesh.rotation.y += 0.02;
                });

                // Particle drift
                particleField.rotation.y = time * 0.02;

                // Parallax response to mouse
                kineticGroup.rotation.x += (targetRotation.x - kineticGroup.rotation.x) * 0.04;
                kineticGroup.rotation.y += (targetRotation.y - kineticGroup.rotation.y) * 0.04;
            }

            renderer.render(scene, camera);
        }

        renderer.setAnimationLoop(animate);

        // Pause loop on tab hidden to save CPU/GPU (as per ui-ux-pro-max guideline)
        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                renderer.setAnimationLoop(null);
            } else {
                clock.getDelta(); // reset delta step
                renderer.setAnimationLoop(animate);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initKineticHero);
    } else {
        initKineticHero();
    }
})();
