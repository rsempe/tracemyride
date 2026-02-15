import { useCallback } from "react";
import { useStore } from "./store";

const translations = {
  en: {
    appSubtitle: "Route generator",
    distance: "Distance",
    loop: "Loop",
    elevationTarget: "Elevation target",
    auto: "Auto",
    generating: "Generating...",
    generateRoute: "Generate route",
    draw: "Draw",
    undo: "Undo",
    confirm: "Confirm",
    clear: "Clear",
    exportGpx: "Export GPX",
    save: "Save",
    routeName: "Route name",
    cancel: "Cancel",
    myRoutes: "My routes",
    noSavedRoutes: "No saved routes",
    delete: "Delete",
    elevationProfile: "Elevation profile",
    elevation: "Elevation",
    clickToPlaceStart: "Click on the map to place the starting point.",
    generationError: "Generation error",
    drawMinPoints: "Place at least 2 points on the map.",
    snapError: "Snap-to-road error",
    unnamedRoute: "Unnamed route",
  },
  fr: {
    appSubtitle: "Générateur d'itinéraires",
    distance: "Distance",
    loop: "Boucle",
    elevationTarget: "Dénivelé cible",
    auto: "Auto",
    generating: "Génération...",
    generateRoute: "Générer un itinéraire",
    draw: "Tracer",
    undo: "Annuler",
    confirm: "Confirmer",
    clear: "Effacer",
    exportGpx: "Exporter GPX",
    save: "Enregistrer",
    routeName: "Nom de l'itinéraire",
    cancel: "Annuler",
    myRoutes: "Mes itinéraires",
    noSavedRoutes: "Aucun itinéraire enregistré",
    delete: "Supprimer",
    elevationProfile: "Profil altimétrique",
    elevation: "Altitude",
    clickToPlaceStart: "Cliquez sur la carte pour placer le point de départ.",
    generationError: "Erreur de génération",
    drawMinPoints: "Placez au moins 2 points sur la carte.",
    snapError: "Erreur de snap-to-road",
    unnamedRoute: "Itinéraire sans nom",
  },
} as const;

export type TranslationKey = keyof typeof translations.en;

export function useTranslation() {
  const locale = useStore((s) => s.locale);
  const setLocale = useStore((s) => s.setLocale);
  const t = useCallback(
    (key: TranslationKey) => translations[locale][key],
    [locale],
  );
  return { t, locale, setLocale };
}
