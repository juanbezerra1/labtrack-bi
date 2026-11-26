// labtrack-bi: query of the table Session (fact_session.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Session.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\fact_session.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Dropped = Table.RemoveColumns(Headers, {"n_recordings", "hours_recorded"}),
    Cleaned = Table.ReplaceValue(Dropped, "", null, Replacer.ReplaceValue, {"session_key", "date_key", "study_key", "participant_key", "researcher_key", "group_label", "visit_no", "room", "status", "duration_min", "starts_local"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"session_key", Int64.Type}, {"date_key", type date}, {"study_key", Int64.Type}, {"participant_key", Int64.Type}, {"researcher_key", Int64.Type}, {"group_label", type text}, {"visit_no", Int64.Type}, {"room", type text}, {"status", type text}, {"duration_min", Int64.Type}, {"starts_local", type datetime}}, "en-US"),
    Labelled = Table.TransformColumns(Typed, {{"group_label", each if _ = null then null else Text.Proper(Text.Replace(_, "_", " ")), type text}, {"status", each if _ = null then null else Text.Proper(Text.Replace(_, "_", " ")), type text}}),
    Renamed = Table.RenameColumns(Labelled, {{"session_key", "Session Key"}, {"date_key", "Session Date"}, {"study_key", "Study Key"}, {"participant_key", "Participant Key"}, {"researcher_key", "Researcher Key"}, {"group_label", "Group"}, {"visit_no", "Visit No"}, {"room", "Room"}, {"status", "Status"}, {"duration_min", "Duration Minutes"}, {"starts_local", "Starts At"}}),
    Selected = Table.SelectColumns(Renamed, {"Session Key", "Session Date", "Study Key", "Participant Key", "Researcher Key", "Group", "Visit No", "Room", "Status", "Duration Minutes", "Starts At"})
in
    Selected
