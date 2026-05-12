export type MeetingFilters = {
  q?: string;
  tag?: string;
  status?: string;
  source_type?: string;
};

export type SavedMeetingView = {
  id: number;
  workspace_id: number;
  name: string;
  filters: MeetingFilters;
  created_at: string;
};

export function cleanedFilters(filters: MeetingFilters) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => Boolean(value?.trim())),
  ) as MeetingFilters;
}

export function meetingFiltersHref(filters: MeetingFilters) {
  const params = new URLSearchParams();
  Object.entries(cleanedFilters(filters)).forEach(([key, value]) => {
    if (value) {
      params.set(key, value);
    }
  });
  const query = params.toString();
  return query ? `/meetings?${query}` : "/meetings";
}
