<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePresentationStore } from '@/stores/presentation'
import UserDirectory from '@/components/presentation/UserDirectory.vue'
import ProfileOverview from '@/components/presentation/ProfileOverview.vue'
import RawVsAdjusted from '@/components/presentation/RawVsAdjusted.vue'
import ActuarialDebugTable from '@/components/presentation/ActuarialDebugTable.vue'
import ThresholdCalibration from '@/components/presentation/ThresholdCalibration.vue'

const store = usePresentationStore()
const route = useRoute()
const router = useRouter()

onMounted(async () => {
  if (!store.isLoaded) {
    await store.loadData()
  }
  
  // Watch query params and update store
  const userQuery = route.query.user as string
  if (userQuery) {
    store.setSelectedUser(userQuery)
  } else {
    store.setSelectedUser(null)
  }
})

// Also watch for query changes dynamically if needed, 
// though Vue Router usually requires watcher or updated hooks
</script>

<template>
  <div class="flex-1 overflow-auto bg-background p-6">
    <div v-if="!store.isLoaded && !store.isError" class="flex h-full items-center justify-center">
      <div class="text-muted-foreground animate-pulse">Loading presentation data...</div>
    </div>
    
    <div v-else-if="store.isError" class="flex h-full flex-col items-center justify-center text-center">
      <h2 class="text-2xl font-bold text-destructive mb-2">Error Loading Data</h2>
      <p class="text-muted-foreground">{{ store.errorMessage }}</p>
    </div>
    
    <div v-else class="h-full">
      <template v-if="store.selectedUserId">
        <ProfileOverview />
        <RawVsAdjusted />
        
        <template v-if="store.isResearchMode">
          <ActuarialDebugTable />
          <ThresholdCalibration />
        </template>
      </template>
      <UserDirectory v-else />
    </div>
  </div>
</template>
