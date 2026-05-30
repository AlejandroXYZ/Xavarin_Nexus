document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("stepForm");
  const formContainer = document.getElementById("formContainer");
  const successScreen = document.getElementById("successScreen");
  const steps = document.querySelectorAll(".step");
  const nextBtns = document.querySelectorAll(".next-btn");
  const prevBtns = document.querySelectorAll(".prev-btn");
  const progressBar = document.getElementById("progressBar");

  const nameInput = document.getElementById("name");
  const displayCompanyName = document.getElementById("displayCompanyName");

  const planCards = document.querySelectorAll(".plan-card");
  const paymentPlanInput = document.getElementById("payment_plan");
  const plansContainer = document.getElementById("plansContainer");

  const odooYes = document.getElementById("odoo_yes");
  const odooNo = document.getElementById("odoo_no");
  const odooUrlWrapper = document.getElementById("odoo_url_wrapper");
  const odooUrlInput = document.getElementById("odoo_url");

  // Lista de países hispanohablantes + EE.UU con sus banderas (Puedes añadir más si lo deseas)
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
  // Llenar el buscador de Países (Datalist)
  const countryList = document.getElementById("country_list");
  if (countryList) {
    countriesData.forEach((c) => {
      const option = document.createElement("option");
      // Al usar datalist, el 'value' es lo que se autocompleta en el texto
      option.value = `${c.flag} ${c.name}`;
      countryList.appendChild(option);
    });
  }

  // Inicialización del número telefónico con banderas
  const phoneInput = document.querySelector("#phone_number");
  const iti = window.intlTelInput(phoneInput, {
    initialCountry: "ve", // Empieza en Venezuela (+58)
    separateDialCode: true, // Separa el +58 del campo de texto
    strictMode: true, // Formatea automáticamente (pone guiones) y bloquea letras
    dropdownContainer: document.body,
    utilsScript:
      "https://cdn.jsdelivr.net/npm/intl-tel-input@23.0.4/build/js/utils.js", // Script que sabe cómo formatear cada país
  });

  function toggleOdoo() {
    if (odooYes.checked) {
      odooUrlWrapper.style.display = "block";
    } else {
      odooUrlWrapper.style.display = "none";
      odooUrlInput.value = ""; // Limpiar el input si se arrepiente y marca "No"
    }
  }

  odooYes.addEventListener("change", toggleOdoo);
  odooNo.addEventListener("change", toggleOdoo);

  let currentStepIndex = 0;

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
        // Scroll top automático si el usuario baja mucho en una ventana larga y pasa a otra corta
        step.scrollTop = 0;

        const firstInput = step.querySelector(
          'input:not([type="hidden"]):not([style*="opacity:0"]), select, textarea',
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

      // Validación especial para el número de teléfono con la librería
      if (input.id === "phone_number" && !iti.isValidNumber()) {
        isInputValid = false;
        // Asignamos un mensaje temporal para que el navegador lo muestre si hace hover
        input.title = "Número de teléfono incompleto o inválido para este país";
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
          if (input.id === "phone_number") input.title = ""; // limpiar título
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

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    // 1. Ejecutar todas las validaciones (campos vacíos, formato, y librería de teléfono)
    if (!validateCurrentStep()) return;

    // 2. Recopilar datos base
    const formData = new FormData(form);
    const formProps = Object.fromEntries(formData);

    // Extraer número de teléfono validado con código de país
    formProps.phone_number = iti.getNumber();

    // 3. Procesar lógica de Odoo
    if (formProps.uses_odoo === "no" || !formProps.odoo_url) {
      formProps.odoo_url = "Generado automáticamente por el sistema";
    }
    delete formProps.uses_odoo;

    // 4. Procesar y agrupar Redes Sociales en un JSON anidado
    formProps.social_networks = {};
    if (formProps.social_instagram)
      formProps.social_networks.instagram = formProps.social_instagram;
    if (formProps.social_facebook)
      formProps.social_networks.facebook = formProps.social_facebook;
    if (formProps.social_linkedin)
      formProps.social_networks.linkedin = formProps.social_linkedin;

    if (Object.keys(formProps.social_networks).length === 0) {
      formProps.social_networks = null;
    }

    delete formProps.social_instagram;
    delete formProps.social_facebook;
    delete formProps.social_linkedin;

    // 5. Preparar el botón de carga
    const submitBtn = document.getElementById("submitBtn");
    submitBtn.innerHTML = "Enviando... ⏳";
    submitBtn.disabled = true;

    // =========================================================
    // 6. ENVIAR DATOS AL BACKEND (COMUNICACIÓN CON TU API)
    // =========================================================

    // *Reemplaza la URL de abajo con la ruta real de tu Backend (Ej: /api/crear-tenant)*
    fetch("/api/recibir-datos-onboarding", {
      method: "POST",
      headers: {
        "Content-Type": "application/json", // Le decimos al Backend que le enviamos un JSON
      },
      body: JSON.stringify(formProps),
    })
      .then((response) => {
        if (response.ok) {
          // Si el Backend guardó los datos y respondió OK, cambiamos de página
          // *Reemplaza esto con la URL o ruta a la que tu backend sirve exito.html*
          window.location.href = "exito.html";
        } else {
          // Si el Backend lanza un error (ej. faltaron datos)
          alert(
            "Hubo un error al procesar tu solicitud. Por favor intenta de nuevo.",
          );
          submitBtn.innerHTML = "Finalizar 🎉";
          submitBtn.disabled = false;
        }
      })
      .catch((error) => {
        // Si el servidor está caído o no hay internet
        console.error("Error de conexión:", error);
        alert("No se pudo conectar con el servidor.");
        submitBtn.innerHTML = "Finalizar 🎉";
        submitBtn.disabled = false;
      });
  });

  updateSteps();
});
