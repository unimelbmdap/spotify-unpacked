// Bump this whenever the consent copy in ConsentText.vue changes. The
// backend rejects donations whose consent_version doesn't match its own
// configured version (see backend/app/config.py `consent_version` and
// backend/consent/*.md), so update both sides together.
export const CONSENT_VERSION = 'v1.0'
