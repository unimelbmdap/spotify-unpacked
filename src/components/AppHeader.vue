<script setup lang="ts">
import { ref } from 'vue'
import { useColorMode } from '@vueuse/core'
import { Moon, Sun } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

const isOpen = ref(false)

const colourMode = useColorMode({
  emitAuto: true,
  storageKey: 'spotify-unpacked-colour-mode',
})

const navLinks = [
  { to: '/', name: 'dashboard', label: 'Upload' },
  { to: '/interviewer', name: 'interviewer', label: 'Interviewer' },
  { to: '/myspotify', name: 'myspotify', label: 'Participant' },
]
</script>

<template>
  <header class="bg-background border-b flex h-12 shrink-0 items-center justify-between px-4">
    <div class="flex items-center gap-6">
      <span class="text-base font-semibold">Spotify Unpacked</span>

      <nav class="flex items-center gap-4">
        <RouterLink
          v-for="link in navLinks"
          :key="link.name"
          :to="link.to"
          class="text-sm transition-colors"
          :class="
            $route.name === link.name
              ? 'text-foreground font-medium'
              : 'text-muted-foreground hover:text-foreground'
          "
        >
          {{ link.label }}
        </RouterLink>
      </nav>
    </div>

    <div class="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="outline" size="icon" class="size-8">
            <Sun class="size-4 scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
            <Moon
              class="absolute size-4 scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0"
            />
            <span class="sr-only">Toggle theme</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem @click="colourMode = 'light'"> Light </DropdownMenuItem>
          <DropdownMenuItem @click="colourMode = 'dark'"> Dark </DropdownMenuItem>
          <DropdownMenuItem @click="colourMode = 'auto'"> System </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Popover v-model:open="isOpen">
        <PopoverTrigger as-child>
          <button class="text-muted-foreground hover:text-foreground text-sm transition-colors">
            About
          </button>
        </PopoverTrigger>

        <Teleport to="body">
          <div
            v-if="isOpen"
            class="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px]"
            @click="isOpen = false"
          />
        </Teleport>

        <PopoverContent align="end" class="z-50 w-96">
          <div class="space-y-2">
            <h4 class="text-sm font-semibold">About Spotify Unpacked</h4>
            <p class="text-muted-foreground text-sm">
              An interactive tool for exploring your Spotify data export. All processing happens
              locally in your browser.
            </p>
            <p class="text-muted-foreground text-sm">
              Built by
              <!-- TODO: add names and links -->
            </p>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  </header>
</template>
