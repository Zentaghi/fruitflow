const q = (id) => document.getElementById(id);

fetch(`status.json?t=${Date.now()}`)
  .then((response) => {
    if (!response.ok) throw new Error("Statut indisponible");
    return response.json();
  })
  .then((status) => {
    q("queue").textContent = status.queueCount ?? 0;
    q("used").textContent = status.usedCount ?? 0;
    q("updated").textContent = status.updatedAt
      ? `Actualisé le ${new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "short" }).format(new Date(status.updatedAt))}`
      : "En attente du premier lancement";
    q("next").textContent = status.nextPost
      ? new Intl.DateTimeFormat("fr-FR", { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Paris" }).format(new Date(status.nextPost))
      : "Aucune";
  })
  .catch(() => { q("updated").textContent = "Statut momentanément indisponible"; });
