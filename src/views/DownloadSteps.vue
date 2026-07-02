<script setup lang="ts">
import { RouterLink } from "vue-router";

const panels = [
  {
    src: `${import.meta.env.BASE_URL}Panel1_DownloadTitle.png`,
    alt: "Instructions on how to download your Spotify data",
  },
  {
    src: `${import.meta.env.BASE_URL}Panel2_Explain.png`,
    alt: "The download files you donate have your listening history and account data to understand what you listen to in 2025 from your library and from the Spotify algorithm.",
  },
  {
    src: `${import.meta.env.BASE_URL}Panel3_OpenWebBrowser.png`,
    alt: "Log into Spotify in a browser",
  },
  {
    src: `${import.meta.env.BASE_URL}Panel4_AccessAccount.png`,
    alt: "Go to your account settings",
  },
  {
    src: `${import.meta.env.BASE_URL}Panel5_SelectAccountPrivacy.png`,
    alt: "Navigate to the Security and Privacy section",
  },
  {
    src: `${import.meta.env.BASE_URL}Panel6_RequestData.png`,
    alt: "Choose to download your Account Data and Extended streaming history",
  },
  {
    src: `${import.meta.env.BASE_URL}Panel7_Wait.png`,
    alt: "Wait for your data request to be processed",
  },
  {
    src: `${import.meta.env.BASE_URL}Panel8_ThankYou.png`,
    alt: "Thank you for requesting to download your Spotify data. When you donate your files to us, they will be visualised and sent back to you for your records.",
  },
];
</script>

<template>
  <section class="mx-auto max-w-4xl p-6 space-y-6">
    <h1 class="text-2xl font-semibold">Download Instructions</h1>
    <p class="text-muted-foreground">
      Follow these steps to request and download your Spotify data.
    </p>

    <main class="panels">
      <figure v-for="panel in panels" :key="panel.src">
        <a
          v-if="panel.src.includes('Panel3_OpenWebBrowser')"
          href="https://open.spotify.com/"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-block cursor-pointer hover:opacity-80 transition-opacity"
        >
          <img :src="panel.src" :alt="panel.alt" />
        </a>
        <img v-else :src="panel.src" :alt="panel.alt" />
      </figure>
    </main>
    <RouterLink to="/">
      <button class="text-sm underline">Back to Dashboard</button>
    </RouterLink>
  </section>
</template>
