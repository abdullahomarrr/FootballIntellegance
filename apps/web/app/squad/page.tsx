import { redirect } from "next/navigation";

/** The squad budget view now lives on Shortlists as the "Coverage & budget" tab. */
export default function SquadPage() {
  redirect("/shortlists?view=plan");
}
