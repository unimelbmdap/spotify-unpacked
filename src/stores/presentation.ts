import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import Papa from 'papaparse'

export interface StudentProfile {
  person_id: string
  profile_label: string
  profile_description: string
  intentionality_band: string
  emotional_range_band: string
  pressure_signal_band: string
  match_coverage_percent: number
  profile_basis_note: string
  profile_conf: number
  heavy_share_raw: number
  heavy_share_cred: number
  upbeat_share_raw: number
  upbeat_share_cred: number
  exam_peak_share_raw: number
  exam_tail_ratio: number
  disclaimer: string
}

export interface WrappedMeasure {
  person_id: string
  metric_name: string
  metric_value_num: number
  metric_value_text: string
  metric_unit: string
  metric_group: string
  source_table: string
  metric_layer: string
}

export interface WrappedCard {
  person_id: string
  card_order: number
  card_type: string
  headline: string
  subheadline: string
  visual_type: string
  confidence_note: string
}

export const usePresentationStore = defineStore('presentation', () => {
  const isLoaded = ref(false)
  const isError = ref(false)
  const errorMessage = ref('')
  const isResearchMode = ref(false)

  const profilesByUser = ref<Record<string, StudentProfile>>({})
  const measuresByUser = ref<Record<string, WrappedMeasure[]>>({})
  const cardsByUser = ref<Record<string, WrappedCard[]>>({})

  const selectedUserId = ref<string | null>(null)

  const availableUsers = computed(() => Object.keys(profilesByUser.value))

  const selectedProfile = computed(() => {
    if (!selectedUserId.value) return null
    return profilesByUser.value[selectedUserId.value] || null
  })

  const selectedMeasures = computed(() => {
    if (!selectedUserId.value) return []
    return measuresByUser.value[selectedUserId.value] || []
  })

  const selectedCards = computed(() => {
    if (!selectedUserId.value) return []
    // Ensure cards are sorted by card_order
    const cards = [...(cardsByUser.value[selectedUserId.value] || [])]
    return cards.sort((a, b) => a.card_order - b.card_order)
  })

  async function loadData() {
    isLoaded.value = false
    isError.value = false
    
    try {
      const [profilesRes, measuresRes, cardsRes] = await Promise.all([
        fetch('/data/student_profiles.csv'),
        fetch('/data/wrapped_aggregate_measures.csv'),
        fetch('/data/wrapped_cards.csv')
      ])

      if (!profilesRes.ok || !measuresRes.ok || !cardsRes.ok) {
        throw new Error("One or more CSV files could not be found.")
      }

      const [profilesText, measuresText, cardsText] = await Promise.all([
        profilesRes.text(),
        measuresRes.text(),
        cardsRes.text()
      ])

      const profilesParsed = Papa.parse(profilesText, { header: true, dynamicTyping: true, skipEmptyLines: true })
      const measuresParsed = Papa.parse(measuresText, { header: true, dynamicTyping: true, skipEmptyLines: true })
      const cardsParsed = Papa.parse(cardsText, { header: true, dynamicTyping: true, skipEmptyLines: true })

      const newProfiles: Record<string, StudentProfile> = {}
      for (const row of profilesParsed.data as any[]) {
        if (row.person_id) {
          newProfiles[row.person_id] = row
        }
      }
      profilesByUser.value = newProfiles

      const newMeasures: Record<string, WrappedMeasure[]> = {}
      for (const row of measuresParsed.data as any[]) {
        if (row.person_id) {
          if (!newMeasures[row.person_id]) newMeasures[row.person_id] = []
          newMeasures[row.person_id]!.push(row)
        }
      }
      measuresByUser.value = newMeasures

      const newCards: Record<string, WrappedCard[]> = {}
      for (const row of cardsParsed.data as any[]) {
        if (row.person_id) {
          if (!newCards[row.person_id]) newCards[row.person_id] = []
          newCards[row.person_id]!.push(row)
        }
      }
      cardsByUser.value = newCards

      isLoaded.value = true
    } catch (e: any) {
      console.error("Failed to load presentation data:", e)
      isError.value = true
      errorMessage.value = e.message || "Failed to load CSV data"
    }
  }

  function setSelectedUser(userId: string | null) {
    selectedUserId.value = userId
  }

  function setResearchMode(mode: boolean) {
    isResearchMode.value = mode
  }

  return {
    isLoaded,
    isError,
    errorMessage,
    isResearchMode,
    availableUsers,
    profilesByUser,
    measuresByUser,
    cardsByUser,
    selectedUserId,
    selectedProfile,
    selectedMeasures,
    selectedCards,
    loadData,
    setSelectedUser,
    setResearchMode
  }
})
