const dropzone = document.querySelector("[data-dropzone]");

if (dropzone) {
  const input = dropzone.querySelector("input[type=file]");
  const name = dropzone.querySelector("[data-file-name]");
  input.addEventListener("change", () => {
    if (input.files.length) name.textContent = input.files[0].name;
  });
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => dropzone.classList.add("is-dragging"));
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove("is-dragging"));
  });
}
