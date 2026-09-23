<template>
  <v-container
    fluid
    class="d-flex justify-center align-center flex-column fill-height"
    :class="{
      'bg-off-white': !$vuetify.theme.current.dark && !isDark,
    }"
  >
    <v-card
      tag="section"
      class="d-flex flex-column align-center w-100 pa-6"
      max-width="600"
    >
      <AppLogo :size="100" />
      <v-card-title class="text-h5 justify-center pb-3">
        Mealie
      </v-card-title>
      <v-card-text class="text-center">
        <template v-if="status === 'loading'">
          <v-progress-circular
            indeterminate
            color="primary"
            class="mb-4"
          />
          <p>{{ $t('general.loading') || 'Signing in with Zpaceâ€¦' }}</p>
        </template>
        <template v-else-if="status === 'missing'">
          <p>
            Sign in through Zpace to open Mealie. This page does not accept a Mealie password.
          </p>
        </template>
        <template v-else-if="status === 'error'">
          <p>
            Could not sign in with Zpace. Refresh after signing in at the Zpace gate, or contact an admin.
          </p>
        </template>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { useDark, useSessionStorage, whenever } from "@vueuse/core";
import { useLoggedInState } from "~/composables/use-logged-in-state";
import { isSafeRedirectTarget } from "~/lib/validators/redirect";
import { useUserActivityPreferences } from "~/composables/use-users/preferences";

definePageMeta({
  layout: "blank",
});
const isDark = useDark();

const router = useRouter();
const route = useRoute();
const i18n = useI18n();
const auth = useMealieAuth();
const { $axios } = useNuxtApp();
const { loggedIn } = useLoggedInState();
const groupSlug = computed(() => auth.user.value?.groupSlug);
const activityPreferences = useUserActivityPreferences();
const { getDefaultActivityRoute } = useDefaultActivity();

const pendingShareRedirect = useSessionStorage<string | null>("pwa_share_redirect", null);
const status = ref<"loading" | "missing" | "error" | "done">("loading");

useSeoMeta({
  title: i18n.t("user.login"),
});

whenever(
  () => loggedIn.value && groupSlug.value,
  () => {
    const redirectFromQuery = route.query.redirect as string | undefined;
    const redirectTarget = redirectFromQuery ?? pendingShareRedirect.value;
    if (isSafeRedirectTarget(redirectTarget)) {
      pendingShareRedirect.value = null;
      router.push(redirectTarget);
      return;
    }

    const defaultActivityRoute = getDefaultActivityRoute(
      activityPreferences.value.defaultActivity,
      groupSlug.value,
    );
    if (defaultActivityRoute) {
      router.push(defaultActivityRoute);
    }
    else {
      router.push(`/g/${groupSlug.value || ""}`);
    }
  },
  { immediate: true },
);

onMounted(async () => {
  if (loggedIn.value) {
    status.value = "done";
    return;
  }

  try {
    const response = await $axios.get("/api/auth/zpace", { withCredentials: true });
    auth.setToken(response.data.access_token);
    await auth.getSession();
    status.value = "done";
  }
  catch (error: any) {
    if (error?.response?.status === 401) {
      status.value = "missing";
    }
    else {
      console.error(error);
      status.value = "error";
    }
  }
});
</script>

<style lang="css">
.bg-off-white {
  background: #f5f8fa;
}
</style>