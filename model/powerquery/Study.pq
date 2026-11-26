// labtrack-bi: query of the table Study (dim_study.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Study.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\dim_study.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Cleaned = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"study_key", "study_code", "title", "started_on", "ended_on", "planned_visits", "target_n"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"study_key", Int64.Type}, {"study_code", type text}, {"title", type text}, {"started_on", type date}, {"ended_on", type date}, {"planned_visits", Int64.Type}, {"target_n", Int64.Type}}, "en-US"),
    Renamed = Table.RenameColumns(Typed, {{"study_key", "Study Key"}, {"study_code", "Study Code"}, {"title", "Study Title"}, {"started_on", "Started On"}, {"ended_on", "Ended On"}, {"planned_visits", "Planned Visits"}, {"target_n", "Target N"}}),
    Selected = Table.SelectColumns(Renamed, {"Study Key", "Study Code", "Study Title", "Started On", "Ended On", "Planned Visits", "Target N"})
in
    Selected
