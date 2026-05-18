<template>
  <LogList category="sql" title="SQL 日志" description="仅记录慢 SQL 和错误 SQL，保存去参数化后的 SQL 模板。" />
</template>

<script lang="ts" setup>
  import LogList from '../LogList.vue';
</script>
