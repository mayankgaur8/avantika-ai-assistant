import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const LANGUAGES = [
  "English", "Hindi", "German", "French", "Spanish", "Japanese",
  "Mandarin Chinese", "Arabic", "Portuguese", "Russian", "Italian",
  "Korean", "Dutch", "Turkish",
];

export const LEVELS = ["beginner", "intermediate", "advanced"];

export const SCENARIO_TYPES = [
  { value: "airport_arrival", label: "Airport Arrival" },
  { value: "hotel_checkin", label: "Hotel Check-in" },
  { value: "restaurant_ordering", label: "Restaurant Ordering" },
  { value: "shopping", label: "Shopping" },
  { value: "taxi_directions", label: "Taxi / Directions" },
  { value: "medical_emergency", label: "Medical Emergency" },
  { value: "police_station", label: "Police Station" },
  { value: "train_booking", label: "Train / Transport Booking" },
];

export const COACHING_TYPES = [
  { value: "job_interview", label: "Job Interview" },
  { value: "email_writing", label: "Email Writing" },
  { value: "presentation_skills", label: "Presentation Skills" },
  { value: "workplace_conversation", label: "Workplace Conversation" },
  { value: "negotiation", label: "Negotiation" },
  { value: "performance_review", label: "Performance Review" },
];

export const JOB_FIELDS = [
  "Software Engineering", "Healthcare", "Finance", "Marketing",
  "Sales", "Legal", "Education", "Hospitality", "Manufacturing", "Consulting",
];
