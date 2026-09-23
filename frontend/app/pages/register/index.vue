<template>
  <v-container
    fill-height
    fluid
    class="d-flex justify-center align-center flex-column fill-height"
    :class="{
      'bg-off-white': !$vuetify.theme.current.dark && !isDark,
    }"
  >
    <v-card
      class="d-flex flex-column align-center w-100 pa-6"
      max-width="600"
    >
      <AppLogo :size="100" />
      <v-card-title class="text-h5 text-center">
        Registration disabled
      </v-card-title>
      <v-card-text class="text-center">
        Mealie accounts are created automatically when you open Mealie while signed in to Zpace.
        Self-registration is not available.
      </v-card-text>
      <v-card-actions class="justify-center">
        <v-btn
          color="primary"
          to="/login"
        >
          Continue
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { useDark } from "@vueuse/core";

definePageMeta({
  layout: "blank",
});

const isDark = useDark();
const i18n = useI18n();

useSeoMeta({
  title: i18n.t("user-registration.user-registration"),
});
</script>

<style lang="css">
.bg-off-white {
  background: #f5f8fa;
}
</style>