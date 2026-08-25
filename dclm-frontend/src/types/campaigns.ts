export interface Campaign {
  id: number;
  name: string;
  source: number | null;
  source_name: string | null;
  spend: string;
  started_on: string | null;
  ended_on: string | null;
  notes: string;
  enquiries_received: number;
  converted: number;
  conversion_rate: number;
  cost_per_enquiry: number | null;
  /** Null until someone converts. Reporting 0 would read as free. */
  cost_per_newcomer: number | null;
}

export interface CampaignSummary {
  total_spend: number;
  total_enquiries: number;
  total_converted: number;
  cost_per_newcomer: number | null;
  campaigns: number;
}
