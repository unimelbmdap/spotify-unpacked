<script setup lang="ts">
import VisualisationPanel from '@/components/InterviewerVizPanel.vue';
import DataPanel from '@/components/DataPanel.vue';
import ResizablePanelGroup from '@/components/ui/resizable/ResizablePanelGroup.vue';
import ResizablePanel from '@/components/ui/resizable/ResizablePanel.vue';
import ResizableHandle from '@/components/ui/resizable/ResizableHandle.vue';
</script>

<template>
  <ResizablePanelGroup direction="horizontal" class="flex-1">
    <ResizablePanel :default-size="20" :min-size="15" :max-size="30">
      <DataPanel />
    </ResizablePanel>

    <ResizableHandle with-handle />

    <ResizablePanel :default-size="55" :min-size="30">
      <VisualisationPanel />
    </ResizablePanel>

    <ResizableHandle with-handle />

  </ResizablePanelGroup>
</template>
