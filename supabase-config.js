import { createClient } from "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm";

const supabaseUrl = "https://rluhddvevpmmiulisyuf.supabase.co";
const supabaseKey = "ВАШ_РЕАЛЬНЫЙ_ANON_KEY"; // ЗАМЕНИТЕ ЭТО

export const supabase = createClient(supabaseUrl, supabaseKey);

// --- AUTH ---
export async function requireAuth() {
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error || !user) {
        window.location.href = "sun-auth-supabase.html";
        return null;
    }
    return user;
}

// --- DATA ---
export async function getOpenTasks() {
    const { data, error } = await supabase
        .from("tasks")
        .select("*")
        .in("status", ["open", "in_progress"])
        .order("created_at", { ascending: false });
    
    if (error) {
        console.error("Error fetching tasks:", error);
        return [];
    }
    return data || [];
}

export async function getMyProfile(userId) {
    const { data, error } = await supabase
        .from("profiles")
        .select("*")
        .eq("id", userId)
        .single();
    return { data, error };
}

export async function applyToTask(taskId, userId) {
    return await supabase
        .from("task_applications")
        .insert({
            task_id: taskId,
            volunteer_id: userId,
            status: "pending"
        });
}