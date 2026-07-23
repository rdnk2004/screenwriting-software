import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// ---- Scripts ---------------------------------------------------------------

export const listScripts = () => api.get("/scripts/").then((r) => r.data);

export const getScript = (id) => api.get(`/scripts/${id}/`).then((r) => r.data);

export const createScript = (title = "Untitled Script") =>
  api.post("/scripts/", { title }).then((r) => r.data);

export const updateScriptTitle = (id, title) =>
  api.patch(`/scripts/${id}/`, { title }).then((r) => r.data);

export const deleteScript = (id) => api.delete(`/scripts/${id}/`);

// ---- Fountain import/export ------------------------------------------------

/**
 * Upload raw Fountain text to the backend; replaces all scenes/lines.
 * Returns the updated script detail object.
 */
export const importFountain = (scriptId, fountainText) =>
  api
    .post(`/scripts/${scriptId}/import_fountain/`, { text: fountainText })
    .then((r) => r.data);

/**
 * Download Fountain text for a script.
 */
export const exportFountain = (scriptId) =>
  axios
    .get(`/api/scripts/${scriptId}/export_fountain/`, {
      responseType: "text",
    })
    .then((r) => r.data);

/**
 * Download PDF for a script.
 */
export const exportPdf = (scriptId, filename = "script.pdf") => {
  return axios
    .get(`/api/scripts/${scriptId}/export_pdf/`, {
      responseType: "blob",
    })
    .then((response) => {
      const url = window.URL.createObjectURL(
        new Blob([response.data], { type: "application/pdf" })
      );
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    });
};

/**
 * Download Word (.docx) for a script.
 */
export const exportWord = (scriptId, filename = "script.docx") => {
  return axios
    .get(`/api/scripts/${scriptId}/export_word/`, {
      responseType: "blob",
    })
    .then((response) => {
      const url = window.URL.createObjectURL(
        new Blob([response.data], {
          type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        })
      );
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    });
};

// ---- Characters -----------------------------------------------------------

export const listCharacters = (scriptId) =>
  api.get(`/characters/?script=${scriptId}`).then((r) => r.data);

export const createCharacter = (data) =>
  api.post("/characters/", data).then((r) => r.data);

export const updateCharacter = (id, data) =>
  api.patch(`/characters/${id}/`, data).then((r) => r.data);

export const deleteCharacter = (id) => api.delete(`/characters/${id}/`);

export const extractCharacters = (scriptId) =>
  api.post(`/scripts/${scriptId}/extract_characters/`).then((r) => r.data);

export const updateCharacterPosition = (id, pos_x, pos_y) =>
  api.patch(`/characters/${id}/`, { pos_x, pos_y }).then((r) => r.data);

// ---- Relationships --------------------------------------------------------

export const listRelationships = (scriptId) =>
  api.get(`/relationships/?script=${scriptId}`).then((r) => r.data);

export const createRelationship = (data) =>
  api.post("/relationships/", data).then((r) => r.data);

export const updateRelationship = (id, data) =>
  api.patch(`/relationships/${id}/`, data).then((r) => r.data);

export const deleteRelationship = (id) => api.delete(`/relationships/${id}/`);
