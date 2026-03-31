import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";
import { uploadProofAndVerify } from "./proof-upload.js";
export const supabase = createClient(
  "https://rluhddvevpmmiulisyuf.supabase.co",
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJsdWhkZHZldnBtbWl1bGlzeXVmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ4NDMzNTksImV4cCI6MjA5MDQxOTM1OX0.zEixUTeTPzVu-BFdcQryWFqBlQSTC_VM2srkl9zOkbM"
);

// ===== AUTH =====

export async function requireAuth() {
  const { data, error } = await supabase.auth.getUser();

  if (error) {
    console.error("requireAuth error:", error);
  }

  if (!data?.user) {
    window.location.href = "sun-auth-supabase.html";
    return null;
  }

  return data.user;
}

export async function getCurrentUser() {
  const { data, error } = await supabase.auth.getUser();

  if (error) {
    console.error("getCurrentUser error:", error);
    return null;
  }

  return data?.user ?? null;
}

// Доп. сохранение id в localStorage, если нужно для UI
export function getCurrentUserId() {
  return localStorage.getItem("user_id");
}

export function setCurrentUserId(id) {
  if (!id) return;
  localStorage.setItem("user_id", id);
}

export function clearCurrentUserId() {
  localStorage.removeItem("user_id");
}

export async function signOutUser() {
  const { error } = await supabase.auth.signOut();
  if (error) {
    console.error("signOutUser error:", error);
    throw error;
  }
  clearCurrentUserId();
}

// ===== PROFILE =====

export async function getMyProfile() {
  const user = await requireAuth();
  if (!user) return null;

  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (error) {
    console.error("getMyProfile error:", error);
    return null;
  }

  return data;
}

export async function upsertMyProfile(payload) {
  const user = await requireAuth();
  if (!user) {
    return { data: null, error: new Error("Пользователь не авторизован") };
  }

  const cleanPayload = {
    id: user.id,
    role: payload?.role ?? "volunteer",
    full_name: payload?.full_name ?? "",
    bio: payload?.bio ?? "",
    hard_skills: Array.isArray(payload?.hard_skills) ? payload.hard_skills : [],
    soft_skills: Array.isArray(payload?.soft_skills) ? payload.soft_skills : [],
    interests: Array.isArray(payload?.interests) ? payload.interests : [],
    goals: Array.isArray(payload?.goals) ? payload.goals : [],
    location: payload?.location ?? "",
    updated_at: new Date().toISOString()
  };

  const { data, error } = await supabase
    .from("profiles")
    .upsert(cleanPayload, { onConflict: "id" })
    .select()
    .single();

  if (error) {
    console.error("upsertMyProfile error:", error);
  }

  return { data, error };
}

// ===== TASKS =====

export async function getOpenTasks() {
  const { data, error } = await supabase
    .from("tasks")
    .select("*")
    .in("status", ["open", "in_progress"])
    .order("created_at", { ascending: false });

  if (error) {
    console.error("getOpenTasks error:", error);
    return [];
  }

  return data || [];
}

export async function createTask(payload) {
  const user = await requireAuth();
  if (!user) {
    return { data: null, error: new Error("Пользователь не авторизован") };
  }

  const cleanTask = {
    curator_id: user.id,
    title: payload?.title ?? "",
    description: payload?.description ?? "",
    event_date: payload?.event_date ?? null,
    event_time: payload?.event_time ?? "",
    location: payload?.location ?? "",
    hard_skills: Array.isArray(payload?.hard_skills) ? payload.hard_skills : [],
    soft_skills: Array.isArray(payload?.soft_skills) ? payload.soft_skills : [],
    quota: Number(payload?.quota ?? 1),
    requirements: Array.isArray(payload?.requirements) ? payload.requirements : [],
    checklist: Array.isArray(payload?.checklist) ? payload.checklist : [],
    status: payload?.status ?? "open",
    ai_summary: payload?.ai_summary ?? ""
  };

  const { data, error } = await supabase
    .from("tasks")
    .insert(cleanTask)
    .select()
    .single();

  if (error) {
    console.error("createTask error:", error);
  }

  return { data, error };
}

export async function getMyTasks() {
  const user = await requireAuth();
  if (!user) return [];

  const { data, error } = await supabase
    .from("tasks")
    .select("*")
    .eq("curator_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    console.error("getMyTasks error:", error);
    return [];
  }

  return data || [];
}

// ===== APPLICATIONS =====

export async function applyToTask(taskId) {
  const user = await requireAuth();
  if (!user) {
    return { data: null, error: new Error("Пользователь не авторизован") };
  }

  const { data, error } = await supabase
    .from("task_applications")
    .insert({
      task_id: taskId,
      volunteer_id: user.id,
      status: "pending"
    })
    .select()
    .single();

  if (error) {
    console.error("applyToTask error:", error);
  }

  return { data, error };
}

export async function getMyApplications() {
  const user = await requireAuth();
  if (!user) return [];

  const { data, error } = await supabase
    .from("task_applications")
    .select(`
      *,
      tasks (
        id,
        title,
        description,
        event_date,
        event_time,
        location,
        status
      )
    `)
    .eq("volunteer_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    console.error("getMyApplications error:", error);
    return [];
  }

  return data || [];
}

// ===== LEGACY EVENTS (если где-то ещё используются старые страницы) =====

export async function getMyEvents() {
  const user = await requireAuth();
  if (!user) return [];

  const { data, error } = await supabase
    .from("events")
    .select("*")
    .eq("curator_id", user.id)
    .order("created_at", { ascending: false });

  if (error) {
    console.error("getMyEvents error:", error);
    return [];
  }

  return data || [];
}

export async function createEvent(payload) {
  const user = await requireAuth();
  if (!user) {
    return { data: null, error: new Error("Пользователь не авторизован") };
  }

  const { data, error } = await supabase
    .from("events")
    .insert({
      curator_id: user.id,
      ...payload
    })
    .select()
    .single();

  if (error) {
    console.error("createEvent error:", error);
  }

  return { data, error };
}