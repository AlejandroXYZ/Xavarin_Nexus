document.addEventListener("DOMContentLoaded", async () => {
  let tenantDataMock;

  // Ámbito global para reutilizar las credenciales de origen en el envío final
  const ORIGEN_SERVIDOR = window.location.origin;
  let llaveSesion = "";

  try {
    // ==========================================================
    // 1. CONFIGURACIÓN DINÁMICA DE RUTA Y EXTRACCIÓN DE PARÁMETRO
    // ==========================================================
    const rutaCompleta = window.location.pathname;
    const segmentos = rutaCompleta
      .split("/")
      .filter((segmento) => segmento !== "");
    llaveSesion = segmentos[segmentos.length - 1];

    if (!llaveSesion) {
      throw new Error(
        "No se pudo detectar el parámetro de sesión al final de la URL.",
      );
    }

    // Ruta exacta hacia tu endpoint POST de inyección
    const urlInyection = `${ORIGEN_SERVIDOR}/api/v1/tenants/form/admin/${encodeURIComponent(llaveSesion)}/inyection`;

    console.log("Haciendo fetch POST a:", urlInyection);

    const response = await fetch(urlInyection, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      throw new Error(
        `Error del servidor: ${response.status} ${response.statusText}`,
      );
    }

    // Leemos la respuesta como texto plano primero para prevenir errores de parsing JSON
    const textoCrudo = await response.text();

    try {
      tenantDataMock = JSON.parse(textoCrudo);
    } catch (jsonError) {
      throw new Error(
        `El backend devolvió un texto plano inválido. Contenido: "${textoCrudo}"`,
      );
    }
  } catch (error) {
    console.error("Fallo de conexión:", error);
    alert("No se pudieron cargar los datos de la empresa.");
    return; // Detiene la ejecución si falla la carga inicial
  }

  // ==========================================================
  // 2. POBLAR LA VISTA DE SOLO LECTURA
  // ==========================================================
  document.getElementById("view_name").textContent = tenantDataMock.name || "-";
  document.getElementById("view_plan").textContent =
    tenantDataMock.payment_plan || "-";
  document.getElementById("view_tone").textContent =
    tenantDataMock.attention_tone || "-";
  document.getElementById("view_contact").textContent =
    `${tenantDataMock.email || ""} | ${tenantDataMock.phone_number || ""}`;
  document.getElementById("view_description").textContent =
    tenantDataMock.description || "-";
  document.getElementById("view_extra").textContent =
    `Envíos: ${tenantDataMock.shipping_policies || "No especificado"} | Garantías: ${tenantDataMock.warranty_policies || "No especificado"}`;

  // ==========================================================
  // 3. GENERACIÓN DINÁMICA DE CAMPOS DE TOKENS SEGÚN EL PLAN
  // ==========================================================
  const tokensContainer = document.getElementById("dynamicTokensContainer");
  const planBadge = document.getElementById("plan_badge");
  const plan = tenantDataMock.payment_plan;

  planBadge.textContent = plan;

  let requiredPlatforms = [];

  if (plan === "basico") {
    requiredPlatforms = ["Telegram"];
  } else if (plan === "profesional") {
    requiredPlatforms = ["Telegram", "WhatsApp"];
  } else if (plan === "enterprise") {
    requiredPlatforms = ["Telegram", "WhatsApp", "Instagram", "TikTok"];
  }

  tokensContainer.innerHTML = "";
  requiredPlatforms.forEach((platform) => {
    const keyName = platform.toLowerCase();
    const inputHTML = `
            <div class="token-input-group">
                <input type="text" name="token_${keyName}" required 
                       placeholder="Token / API Key para ${platform}">
            </div>
        `;
    tokensContainer.insertAdjacentHTML("beforeend", inputHTML);
  });

  // ==========================================================
  // 4. LÓGICA DE ENVÍO REAL DEL FORMULARIO ADMIN (HACIA FASTAPI)
  // ==========================================================
  const adminForm = document.getElementById("adminSetupForm");

  adminForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(adminForm);
    const adminProps = Object.fromEntries(formData);
    const tokensPlataformas = {};

    // Agrupar los tokens dinámicos en un sub-diccionario
    for (const [key, value] of Object.entries(adminProps)) {
      if (key.startsWith("token_")) {
        const cleanKey = key.replace("token_", "");
        tokensPlataformas[cleanKey] = value;
        delete adminProps[key];
      }
    }

    // Capturamos el System Prompt evaluando mayúsculas y minúsculas de forma segura
    const systemPromptValue =
      adminProps.AI_System_Prompt || adminProps.ai_system_prompt || "";

    // Construcción del JSON Payload final mapeado idénticamente a RegisterData en Python
    const finalJsonPayload = {
      ai_system_prompt: systemPromptValue, // <-- CORREGIDO EN MINÚSCULAS CON SNAKE_CASE
      tokens_platforms: tokensPlataformas,
    };

    const submitBtn = document.getElementById("activateBtn");
    const textoOriginalBtn = submitBtn.innerHTML;

    // Bloquear controles visuales
    submitBtn.innerHTML = "Guardando... ⏳";
    submitBtn.disabled = true;

    // Ruta de registro dinámica en tu backend
    const urlRegister = `${ORIGEN_SERVIDOR}/api/v1/tenants/register/${encodeURIComponent(llaveSesion)}`;

    try {
      console.log("Enviando datos de registro a:", urlRegister);

      const responseRegister = await fetch(urlRegister, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(finalJsonPayload),
      });

      if (!responseRegister.ok) {
        throw new Error(
          `Error al registrar: ${responseRegister.status} ${responseRegister.statusText}`,
        );
      }

      const resultadoRegistro = await responseRegister.json();
      console.log(
        "Servidor procesó la activación con éxito:",
        resultadoRegistro,
      );

      // Mostrar pantalla de éxito integrada en tu HTML
      document.getElementById("successScreen").classList.add("active");
    } catch (error) {
      console.error("Error en el envío del formulario:", error);
      alert("Hubo un error al intentar activar el ecosistema del inquilino.");

      // Restaurar el botón para permitir reintentos al usuario si la transacción falla
      submitBtn.innerHTML = textoOriginalBtn;
      submitBtn.disabled = false;
    }
  });
});
