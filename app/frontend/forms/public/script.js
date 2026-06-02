document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("stepForm");
  const formContainer = document.getElementById("formContainer");
  const steps = document.querySelectorAll(".step");
  const nextBtns = document.querySelectorAll(".next-btn");
  const prevBtns = document.querySelectorAll(".prev-btn");
  const progressBar = document.getElementById("progressBar");

  const nameInput = document.getElementById("name");
  const displayCompanyName = document.getElementById("displayCompanyName");

  const planCards = document.querySelectorAll(".plan-card");
  const paymentPlanInput = document.getElementById("payment_plan");
  const plansContainer = document.getElementById("plansContainer");

  let currentStepIndex = 0;

  // === 1. LIBRERÍA DE TELÉFONO ===
  const phoneInput = document.querySelector("#phone_number");
  const iti = window.intlTelInput(phoneInput, {
    initialCountry: "ve",
    separateDialCode: true,
    strictMode: true,
    dropdownContainer: document.body,
    utilsScript:
      "https://cdn.jsdelivr.net/npm/intl-tel-input@23.0.4/build/js/utils.js",
  });

  // === 2. LISTA DE PAÍSES PARA EL BUSCADOR (DATALIST) ===
  const countriesData = [
    { name: "Argentina", flag: "🇦🇷" },
    { name: "Bolivia", flag: "🇧🇴" },
    { name: "Chile", flag: "🇨🇱" },
    { name: "Colombia", flag: "🇨🇴" },
    { name: "Costa Rica", flag: "🇨🇷" },
    { name: "Ecuador", flag: "🇪🇨" },
    { name: "El Salvador", flag: "🇸🇻" },
    { name: "España", flag: "🇪🇸" },
    { name: "Estados Unidos", flag: "🇺🇸" },
    { name: "Guatemala", flag: "🇬🇹" },
    { name: "Honduras", flag: "🇭🇳" },
    { name: "México", flag: "🇲🇽" },
    { name: "Nicaragua", flag: "🇳🇮" },
    { name: "Panamá", flag: "🇵🇦" },
    { name: "Paraguay", flag: "🇵🇾" },
    { name: "Perú", flag: "🇵🇪" },
    { name: "República Dominicana", flag: "🇩🇴" },
    { name: "Uruguay", flag: "🇺🇾" },
    { name: "Venezuela", flag: "🇻🇪" },
  ];

  const countryList = document.getElementById("country_list");
  if (countryList) {
    countriesData.forEach((c) => {
      const option = document.createElement("option");
      option.value = `${c.flag} ${c.name}`;
      countryList.appendChild(option);
    });
  }

  // === 3. LÓGICA DE MOSTRAR/OCULTAR PREGUNTAS ===
  // Odoo
  const odooYes = document.getElementById("odoo_yes");
  const odooNo = document.getElementById("odoo_no");
  const odooUrlWrapper = document.getElementById("odoo_url_wrapper");
  const odooUrlInput = document.getElementById("odoo_url");

  function toggleOdoo() {
    if (odooYes.checked) {
      odooUrlWrapper.style.display = "block";
    } else {
      odooUrlWrapper.style.display = "none";
      odooUrlInput.value = "";
    }
  }
  odooYes.addEventListener("change", toggleOdoo);
  odooNo.addEventListener("change", toggleOdoo);

  // Envíos
  const shippingYes = document.getElementById("shipping_yes");
  const shippingNo = document.getElementById("shipping_no");
  const shippingDetailsWrapper = document.getElementById(
    "shipping_details_wrapper",
  );
  const shippingInput = document.getElementById("shipping_policies");

  function toggleShipping() {
    if (shippingYes.checked) {
      shippingDetailsWrapper.style.display = "block";
      shippingInput.required = true;
    } else {
      shippingDetailsWrapper.style.display = "none";
      shippingInput.required = false;
      shippingInput.value = "";
    }
  }
  shippingYes.addEventListener("change", toggleShipping);
  shippingNo.addEventListener("change", toggleShipping);

  // Garantías
  const warrantyYes = document.getElementById("warranty_yes");
  const warrantyNo = document.getElementById("warranty_no");
  const warrantyDetailsWrapper = document.getElementById(
    "warranty_details_wrapper",
  );
  const warrantyInput = document.getElementById("warranty_policies");

  function toggleWarranty() {
    if (warrantyYes.checked) {
      warrantyDetailsWrapper.style.display = "block";
      warrantyInput.required = true;
    } else {
      warrantyDetailsWrapper.style.display = "none";
      warrantyInput.required = false;
      warrantyInput.value = "";
    }
  }
  warrantyYes.addEventListener("change", toggleWarranty);
  warrantyNo.addEventListener("change", toggleWarranty);

  // === 4. LÓGICA DE NAVEGACIÓN Y VALIDACIÓN ===
  nameInput.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    displayCompanyName.textContent = val ? val : "tu empresa";
  });

  planCards.forEach((card) => {
    card.addEventListener("click", () => {
      planCards.forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
      paymentPlanInput.value = card.dataset.value;
      plansContainer.classList.remove("input-error");
    });
  });

  function updateSteps() {
    steps.forEach((step, index) => {
      if (index === currentStepIndex) {
        step.classList.add("active");

        step.scrollTop = 0;
        step.scrollLeft = 0;
        const plansBox = step.querySelector(".plans-container");
        if (plansBox) plansBox.scrollLeft = 0;

        const firstInput = step.querySelector(
          'input:not([type="hidden"]):not([style*="opacity: 0"]), select, textarea',
        );
        if (firstInput && window.innerWidth > 768) {
          setTimeout(() => firstInput.focus(), 500);
        }
      } else {
        step.classList.remove("active");
      }
    });

    const progress = ((currentStepIndex + 1) / steps.length) * 100;
    progressBar.style.width = `${progress}%`;
  }

  function validateCurrentStep() {
    const currentStep = steps[currentStepIndex];
    const inputs = currentStep.querySelectorAll("input, select, textarea");
    let isValid = true;

    inputs.forEach((input) => {
      let isInputValid = input.checkValidity();

      if (input.id === "phone_number" && !iti.isValidNumber()) {
        isInputValid = false;
        input.title = "Número de teléfono incompleto o inválido";
      }

      if (!isInputValid) {
        isValid = false;

        let elementToShake = input;
        if (input.id === "payment_plan") elementToShake = plansContainer;

        elementToShake.classList.remove("input-error");
        void elementToShake.offsetWidth;
        elementToShake.classList.add("input-error");

        if (!input.title && input.validationMessage) {
          input.title = input.validationMessage;
        }

        setTimeout(() => {
          elementToShake.classList.remove("input-error");
          if (input.id === "phone_number") input.title = "";
        }, 1500);
      }
    });

    return isValid;
  }

  nextBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (validateCurrentStep()) {
        if (currentStepIndex < steps.length - 1) {
          currentStepIndex++;
          updateSteps();
        }
      }
    });
  });

  prevBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      if (currentStepIndex > 0) {
        currentStepIndex--;
        updateSteps();
      }
    });
  });

  form.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
      e.preventDefault();
      const activeStep = steps[currentStepIndex];
      const nextBtn = activeStep.querySelector(".next-btn");

      if (nextBtn) {
        nextBtn.click();
      } else if (
        currentStepIndex === steps.length - 1 &&
        validateCurrentStep()
      ) {
        form.dispatchEvent(new Event("submit"));
      }
    }
  });

  // === 5. ENVÍO FINAL AL BACKEND ===
  form.addEventListener("submit", (e) => {
    e.preventDefault();

    if (!validateCurrentStep()) return;

    const formData = new FormData(form);
    const formProps = Object.fromEntries(formData);

    // ==========================================================
    // LIMPIEZA ESTRICTA PARA PYDANTIC (FASTAPI)
    // ==========================================================

    // 1. Número Telefónico
    formProps.phone_number = iti.getNumber();

    // 2. Forzar Enums a minúsculas y sin tildes
    if (formProps.payment_plan) {
        formProps.payment_plan = formProps.payment_plan.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }
    if (formProps.attention_tone) {
        if (formProps.attention_tone === "amigable") formProps.attention_tone = "amable";
        formProps.attention_tone = formProps.attention_tone.toLowerCase();
    }

    // 3. Odoo (HttpUrl | None) - Forzar https://
    if (formProps.uses_odoo === "no" || !formProps.odoo_url || formProps.odoo_url.trim() === "") {
      formProps.odoo_url = null; 
    } else {
      if (!/^https?:\/\//i.test(formProps.odoo_url)) {
          formProps.odoo_url = "https://" + formProps.odoo_url;
      }
    }
    delete formProps.uses_odoo;

    // 4. Website (HttpUrl | None) - Forzar https://
    if (!formProps.website || formProps.website.trim() === "") {
      formProps.website = null;
    } else {
      if (!/^https?:\/\//i.test(formProps.website)) {
          formProps.website = "https://" + formProps.website;
      }
    }

    // 5. Transformar strings vacíos a null (Opcionales)
    if (!formProps.exact_address || formProps.exact_address.trim() === "") formProps.exact_address = null;
    if (!formProps.schedule || formProps.schedule.trim() === "") formProps.schedule = null;
    if (!formProps.bank_details || formProps.bank_details.trim() === "") formProps.bank_details = null;

    // 6. Envíos y Garantías
    if (formProps.has_shipping === "no" || !formProps.shipping_policies || formProps.shipping_policies.trim() === "") {
      formProps.shipping_policies = null;
    }
    delete formProps.has_shipping;

    if (formProps.has_warranty === "no" || !formProps.warranty_policies || formProps.warranty_policies.trim() === "") {
      formProps.warranty_policies = null;
    }
    delete formProps.has_warranty;

    // 7. Redes Sociales
    formProps.social_networks = {};
    if (formProps["red social 1"] && formProps["red social 1"].trim() !== "") 
      formProps.social_networks.red_1 = formProps["red social 1"];
    
    if (formProps["red social 2"] && formProps["red social 2"].trim() !== "") 
      formProps.social_networks.red_2 = formProps["red social 2"];
    
    if (formProps["red social 3"] && formProps["red social 3"].trim() !== "") 
      formProps.social_networks.red_3 = formProps["red social 3"];

    if (Object.keys(formProps.social_networks).length === 0) {
      formProps.social_networks = null; 
    }

    delete formProps["red social 1"];
    delete formProps["red social 2"];
    delete formProps["red social 3"];

    // ==========================================================
    // CAPTURAR PARÁMETRO DE SESIÓN DE LA RUTA
    // ==========================================================
    const submitBtn = document.getElementById("submitBtn");
    submitBtn.innerHTML = "Enviando... ⏳";
    submitBtn.disabled = true;

    const currentPath = window.location.pathname.replace(/\/$/, "");
    const sesionId = currentPath.substring(currentPath.lastIndexOf("/") + 1);

    if (!sesionId || sesionId === "public" || sesionId === "form") {
      alert("Error crítico: No se encontró la llave de sesión en la URL.");
      submitBtn.innerHTML = "Finalizar 🎉";
      submitBtn.disabled = false;
      return;
    }

    const apiRoute = `/api/v1/tenants/form/completed/${encodeURIComponent(sesionId)}`;

    // ==========================================================
    // PETICIÓN AL BACKEND CON LECTURA DE ERROR 422
    // ==========================================================
    fetch(apiRoute, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(formProps),
    })
      .then(async (response) => {
        if (response.ok) {
          window.location.href = "/static/forms/public/exito.html";
        } else {
          // Leer la queja exacta de Pydantic
          const errorData = await response.json();
          console.error("FastAPI rechazó los datos:", errorData);
          
          alert("FastAPI rechazó los datos (Error " + response.status + ").\n\nMotivo:\n" + JSON.stringify(errorData.detail, null, 2));
          
          submitBtn.innerHTML = "Finalizar 🎉";
          submitBtn.disabled = false;
        }
      })
      .catch((error) => {
        console.error("Error de conexión:", error);
        alert("Error de conexión. Revisa la consola.");
        submitBtn.innerHTML = "Finalizar 🎉";
        submitBtn.disabled = false;
      });
  });

  updateSteps();
});
