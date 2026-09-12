/*
 * FQQ v0.20 — QUANTITY axis: "how much does this body need now?"
 *
 * Deliberately 100% client-side. Nothing here is ever sent to or stored by
 * the food.bringon.io server — see /behoefte and CLAUDE.md for why. This
 * file is loaded by both behoefte.html (the calculator) and product.html
 * (to show "X% of what you still need today" when a profile is saved).
 *
 * Formulas used, all real and citable — NOT reverse-engineered to match any
 * specific numbers, chosen because they are the standard, defensible ones:
 *   - Katch-McArdle (1996):    RMR = 370 + 21.6 * FFM(kg)
 *   - Mifflin-St Jeor (1990):  RMR = 10*weight(kg) + 6.25*height(cm) - 5*age(y) + 5 (men)
 *                                                                              - 161 (women)
 *   - Standard PAL activity multipliers (sedentary..very active): 1.2 - 1.9
 *   - EU reference intake (nutrition-label standard): 2000 kcal/day, average adult
 *
 * What this deliberately does NOT do, and why (see CLAUDE.md):
 *   - No geography-based prior. The original FQQ v0.20 prototype used
 *     synthetic region/district data with Bayesian shrinkage; shipping that
 *     with real population data risks reading as a claim about what people
 *     "from X region" need, even unintentionally. Skipped rather than done
 *     half-safely.
 *   - No FORM (can-this-person-eat-this) safety filtering, e.g. allergens.
 *     A false negative there is a real safety risk and needs a far more
 *     rigorous, validated dataset than this project has.
 *   - Every number here is a population-average ESTIMATE, never measured
 *     metabolism, and this is a research prototype, not medical or dietary
 *     advice — said once here, and said again in the UI, on purpose.
 */

const FQQ_STORAGE_KEY = "food-bringon-quantity-profile-v1";

const FQQ_ACTIVITY_MULTIPLIERS = {
  sedentary: 1.2,
  light: 1.375,
  moderate: 1.55,
  active: 1.725,
  very_active: 1.9,
};

const FQQ_ACTIVITY_LABELS = {
  sedentary: "Weinig tot geen beweging",
  light: "Licht actief (1-3 dagen/week sport)",
  moderate: "Matig actief (3-5 dagen/week sport)",
  active: "Actief (6-7 dagen/week sport)",
  very_active: "Zeer actief (zwaar fysiek werk of 2x/dag training)",
};

function fqqNum(v) {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : null;
}

/** Personalization fallback hierarchy: measured REE > FFM (Katch-McArdle)
 * > age/sex/height/weight (Mifflin-St Jeor) > no personal data. */
function fqqComputeREE(profile) {
  const measured = fqqNum(profile.measuredReeKcal);
  if (measured !== null && measured > 0) {
    return { value: measured, source: "Gemeten rustmetabolisme", confidence: "hoog" };
  }

  const ffm = fqqNum(profile.ffmKg);
  if (ffm !== null && ffm > 0) {
    return {
      value: 370 + 21.6 * ffm,
      source: "Katch-McArdle-schatting (vetvrije massa)",
      confidence: "gemiddeld",
    };
  }

  const weight = fqqNum(profile.weightKg);
  const height = fqqNum(profile.heightCm);
  const age = fqqNum(profile.ageYears);
  const sex = profile.sex;
  if (weight !== null && height !== null && age !== null && (sex === "m" || sex === "v")) {
    const base = 10 * weight + 6.25 * height - 5 * age;
    return {
      value: sex === "m" ? base + 5 : base - 161,
      source: "Mifflin-St Jeor-schatting",
      confidence: "gemiddeld-laag",
    };
  }

  return { value: null, source: null, confidence: null };
}

/** Daily energy target. Falls back to the EU reference-intake figure
 * (already a whole-day number, so no activity multiplier applied to it —
 * that would double-count) when no personal data is available at all. */
function fqqComputeDailyTarget(profile) {
  const ree = fqqComputeREE(profile);
  const extra = fqqNum(profile.extraExerciseKcal) || 0;

  if (ree.value === null) {
    return {
      tdee: 2000,
      ree: null,
      reeSource: null,
      source: "Algemene referentie-inname (EU-voedingswaarde-etiket, gemiddelde volwassene)",
      confidence: "laag",
    };
  }

  const mult = FQQ_ACTIVITY_MULTIPLIERS[profile.activityLevel] || FQQ_ACTIVITY_MULTIPLIERS.sedentary;
  return {
    tdee: ree.value * mult + extra,
    ree: ree.value,
    reeSource: ree.source,
    source: ree.source,
    confidence: ree.confidence,
  };
}

/** Adds "what's already been eaten today" to get what's left. */
function fqqRemainingNeed(profile) {
  const target = fqqComputeDailyTarget(profile);
  const consumed = fqqNum(profile.consumedTodayKcal) || 0;
  return {
    ...target,
    consumed,
    remaining: Math.max(target.tdee - consumed, 0),
    surplus: Math.max(consumed - target.tdee, 0),
  };
}

function fqqSaveProfile(profile) {
  try {
    localStorage.setItem(FQQ_STORAGE_KEY, JSON.stringify(profile));
  } catch (e) {
    /* private-browsing / storage blocked — degrade silently, nothing to save server-side anyway */
  }
}

function fqqLoadProfile() {
  try {
    const raw = localStorage.getItem(FQQ_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function fqqClearProfile() {
  try {
    localStorage.removeItem(FQQ_STORAGE_KEY);
  } catch (e) {
    /* nothing to clear if storage never worked */
  }
}
