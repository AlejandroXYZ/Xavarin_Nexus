document.addEventListener("DOMContentLoaded", () => {
    
    // ==========================================================
    // 1. SIMULACIÓN DE DATOS INYECTADOS POR EL BACKEND
    // En producción, podrías inyectar esto con Jinja2 o hacer un fetch() a tu API
    // ==========================================================
    const tenantDataMock = {
        name: "TechNova C.A.",
        email: "operaciones@technovaca.com",
        phone_number: "+584121234567",
        payment_plan: "enterprise", // Puede ser: "basico", "profesional", "enterprise"
        attention_tone: "entusiasta",
        description: "Desarrollo web y digitalización de negocios retail.",
        shipping_policies: "Envíos nacionales vía MRW.",
        warranty_policies: "30 días por software."
    };

    // ==========================================================
    // 2. POBLAR LA VISTA DE SOLO LECTURA
    // ==========================================================
    document.getElementById("view_name").textContent = tenantDataMock.name;
    document.getElementById("view_plan").textContent = tenantDataMock.payment_plan;
    document.getElementById("view_tone").textContent = tenantDataMock.attention_tone;
    document.getElementById("view_contact").textContent = `${tenantDataMock.email} | ${tenantDataMock.phone_number}`;
    document.getElementById("view_description").textContent = tenantDataMock.description;
    document.getElementById("view_extra").textContent = `Envíos: ${tenantDataMock.shipping_policies} | Garantías: ${tenantDataMock.warranty_policies}`;

    // ==========================================================
    // 3. GENERACIÓN DINÁMICA DE CAMPOS DE TOKENS SEGÚN EL PLAN
    // ==========================================================
    const tokensContainer = document.getElementById("dynamicTokensContainer");
    const planBadge = document.getElementById("plan_badge");
    const plan = tenantDataMock.payment_plan;
    
    planBadge.textContent = plan; // Mostrar el plan en la etiqueta azul

    // Lógica de plataformas según el plan de la empresa SaaS
    let requiredPlatforms = [];
    
    if (plan === "basico") {
        requiredPlatforms = ["Telegram"];
    } else if (plan === "profesional") {
        requiredPlatforms = ["Telegram", "WhatsApp"];
    } else if (plan === "enterprise") {
        requiredPlatforms = ["Telegram", "WhatsApp", "Instagram", "TikTok"];
    }

    // Inyectar los inputs al HTML
    requiredPlatforms.forEach(platform => {
        // Convertimos el nombre a formato llave de diccionario (ej: "Telegram" -> "telegram")
        const keyName = platform.toLowerCase();
        
        const inputHTML = `
            <div class="token-input-group">
                <input type="text" name="token_${keyName}" required 
                       placeholder="Token / API Key para ${platform}">
            </div>
        `;
        tokensContainer.insertAdjacentHTML('beforeend', inputHTML);
    });

    // ==========================================================
    // 4. LÓGICA DE ENVÍO DEL FORMULARIO ADMIN (HACIA FASTAPI)
    // ==========================================================
    const adminForm = document.getElementById("adminSetupForm");
    
    adminForm.addEventListener("submit", (e) => {
        e.preventDefault();

        const formData = new FormData(adminForm);
        const adminProps = Object.fromEntries(formData);

        // Estructura final adaptada a Pydantic
        // Construimos el diccionario de tokens de plataformas
        const tokensPlataformas = {};
        
        // Buscamos todas las llaves que empiezan con "token_" en el formulario
        for (const [key, value] of Object.entries(adminProps)) {
            if (key.startsWith("token_")) {
                const cleanKey = key.replace("token_", "");
                tokensPlataformas[cleanKey] = value;
                // Borramos la clave suelta para que no quede sucia
                delete adminProps[key];
            }
        }

        // Armamos el JSON final que coincidirá con tu BaseModel
        const finalJsonPayload = {
            AI_System_Prompt: adminProps.AI_System_Prompt,
            tokens_plataformas: tokensPlataformas
        };

        const submitBtn = document.getElementById("activateBtn");
        submitBtn.innerHTML = "Guardando... ⏳";
        submitBtn.disabled = true;

        // Simulación del Fetch al Backend
        setTimeout(() => {
            console.log("=== DATOS DE ACTIVACIÓN ADMIN (JSON) ===");
            console.log(JSON.stringify(finalJsonPayload, null, 2));

            // Mostrar pantalla de éxito
            document.getElementById("successScreen").classList.add("active");
            
        }, 1200);

        /* EJEMPLO DE ENVÍO REAL:
        fetch('/api/activar-inquilino/ID_AQUI', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(finalJsonPayload)
        }).then(...)
        */
    });
});
