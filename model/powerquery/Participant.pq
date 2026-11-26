// labtrack-bi: query of the table Participant (dim_participant.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Participant.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\dim_participant.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Cleaned = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"participant_key", "participant_code", "birth_year", "sex", "dominant_hand", "consent_signed_on", "withdrawn_on", "is_withdrawn"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"participant_key", Int64.Type}, {"participant_code", type text}, {"birth_year", Int64.Type}, {"sex", type text}, {"dominant_hand", type text}, {"consent_signed_on", type date}, {"withdrawn_on", type date}, {"is_withdrawn", type logical}}, "en-US"),
    Labelled = Table.TransformColumns(Typed, {{"dominant_hand", each if _ = null then null else Text.Proper(Text.Replace(_, "_", " ")), type text}}),
    AddStatus = Table.AddColumn(Labelled, "Status", each if [is_withdrawn] then "Withdrawn" else "Active", type text),
    AddAgeAtConsent = Table.AddColumn(AddStatus, "Age at Consent", each Date.Year([consent_signed_on]) - [birth_year], Int64.Type),
    AddAgeBand = Table.AddColumn(AddAgeAtConsent, "Age Band", each if [Age at Consent] < 30 then "Under 30" else if [Age at Consent] < 45 then "30-44" else if [Age at Consent] < 60 then "45-59" else "60+", type text),
    AddAgeBandOrder = Table.AddColumn(AddAgeBand, "Age Band Order", each if [Age at Consent] < 30 then 1 else if [Age at Consent] < 45 then 2 else if [Age at Consent] < 60 then 3 else 4, Int64.Type),
    Renamed = Table.RenameColumns(AddAgeBandOrder, {{"participant_key", "Participant Key"}, {"participant_code", "Participant Code"}, {"birth_year", "Birth Year"}, {"sex", "Sex"}, {"dominant_hand", "Dominant Hand"}, {"consent_signed_on", "Consent Date"}, {"withdrawn_on", "Withdrawn On"}, {"is_withdrawn", "Is Withdrawn"}}),
    Selected = Table.SelectColumns(Renamed, {"Participant Key", "Participant Code", "Birth Year", "Sex", "Dominant Hand", "Consent Date", "Withdrawn On", "Is Withdrawn", "Status", "Age at Consent", "Age Band", "Age Band Order"})
in
    Selected
