(:~ 
  : This script provides the functions that build or update edirom annots
  :
  : @author Silke Reich
  : @version 0.1
:)

(: TODOs:
    - Musikalische Symbole anzeigen => Problem auf Seiten der Edirom-Programmierung
    - Scan-Ausschnitte anzeigen => checken, wenn dev-Ansicht funktioniert
:)

xquery version "3.1";

declare namespace edirom = "http://www.edirom.de/ns/1.3";
declare namespace mei = "http://www.music-encoding.org/ns/mei";
declare namespace transform = "http://exist-db.org/xquery/transform";
declare namespace xmldb = "http://exist-db.org/xquery/xmldb";
declare namespace array = "http://www.w3.org/2005/xpath-functions/array";
declare namespace util = "http://exist-db.org/xquery/util";
declare namespace map = "http://www.w3.org/2005/xpath-functions/map";
declare namespace math = "http://www.w3.org/2005/xpath-functions/math";

(: External variables - can be passed from the command line with -b option :)
declare variable $cnList as xs:string? external := "";
declare variable $cnListFile as xs:string? external := "";
declare variable $collectionPath as xs:string external;
declare variable $sourcesPath as xs:string external;
declare variable $editionHandle as xs:string external;
declare variable $volumeName as xs:string external;

declare function local:normalize-text-nodes($node as node()) as node() {
  typeswitch($node)
    case text() 
      return 
        if (normalize-space($node) = '') then 
          $node 
        else 
          text { normalize-space($node) }
    case element() return element { node-name($node) } {
      $node/@*,
      for $child in $node/node()
      return local:normalize-text-nodes($child)
    }
    default return $node
};

declare function local:textRendition($node as node()?) as item()* {
  <rend
    xmlns="http://www.music-encoding.org/ns/mei"
    rend="{
        if ($node/@rend/normalize-space() = 'it') then
          'italic'
        else
          $node/@rend/normalize-space()
      }">{$node/normalize-space()}</rend>
};

declare function local:buildSiglum($node as node()?, $sources as node()*, $editionHandle as xs:string, $volumeName as xs:string) as item()* {
  let $sourceDoc := $sources//mei:mei[.//mei:identifier[text() = $node/@siglum/normalize-space()]][1]
  let $filename := if ($sourceDoc) then
    replace(base-uri($sourceDoc), '^(.*/)(.*?)\.\w+$', '$2')
  else
    "unknown"
  return
    <ref
      xmlns="http://www.music-encoding.org/ns/mei"
      target="xmldb:exist:///db/apps/edirom-content/{$volumeName}/{$editionHandle}/sources/{$filename}.xml">{$node/@siglum/normalize-space()}</ref>
};

(:~
: Building a string from multiple measures or measure sequences that are children from measures.
: @param $measures Node that contains one or more measures or sequences of measures.
: @return Measures as string.
:)
declare function local:buildMeasures($measures as node()?) as xs:string* {
  let $measures-string := for $node in $measures/*
  return
    switch ($node/name())
      case 'measure'
        return
          $node/@label/string()
      case 'sequence'
        return
          concat($node/@label-from/string(), '–', $node/@label-to/string())
      default
      return
        ""
return
  ('T. ', string-join($measures-string, ', '))
};

(:~
: Extracts the pitch name and octave pitch elements .
: @param $pitch Pitch node.
: @return Pitch name and octave.
:)
declare function local:buildPitch($pitch as node()*) as item()* {
  let $pname := if (xs:int($pitch/@oct/normalize-space()) <= 2)
  then
    upper-case($pitch/@pname/normalize-space())
  else
    $pitch/@pname/normalize-space()
  let $oct := if (xs:int($pitch/@oct/normalize-space()) >= 4)
  then
    xs:int($pitch/@oct/normalize-space()) - 3
  else
    if (xs:int($pitch/@oct/normalize-space()) >= 2)
    then
      ()
    else
      if (xs:int($pitch/@oct/normalize-space()) = 1)
      then
        (1)
      else
        ("###ERROR###")
  return
    <rend
      xmlns="http://www.music-encoding.org/ns/mei"
      rend="italic">{$pname}<rend
        rend="superscript">{$oct}</rend></rend>
};


(:~
: Extracts the pitch name and octave within chords and returns them according to the EWK-WA guidelines.
: @param $chord Chord node.
: @return Pitch names and octaves for all pitches within the chord seperated by slashes.
:)
declare function local:buildChord($chord as node()*) as item()* {
  for $pitch in $chord/pitch
  return
    if ($pitch is $chord/pitch[last()]) then
      (
      local:buildPitch($pitch))
    else
      (
      concat(local:buildPitch($pitch), '/')
      )
};

(:~
: Extracts the pitch name and octave within sequences and returns them according to the EWK-WA guidelines.
: @param $sequences Sequence node.
: @return Pitch names and octaves for all pitches within the chord seperated by dashes.
:)
declare function local:buildSequence($sequence as node()*) as item()* {
  for $pitch in $sequence/pitch
  return
    if ($pitch is $sequence/pitch[last()]) then
      (
      local:buildPitch($pitch))
    else
      (
      concat(local:buildPitch($pitch), '–')
      )
};

(:~
: Transforms the musicalSymbal URL to a TEI graphic.
: @param $symbol Smufl png URL.
: @return TEI graphic element for smufl.
:)
declare function local:buildSmufl($symbol as xs:string) as item()* {
  let $url := fn:replace($symbol, '.png', '.xml')
  return
    <graphic
      xmlns="http://www.music-encoding.org/ns/mei"
      ref="{$url}"
      type="smufl"/>
};

(:~
: Builds noteText content with proper spacing before siglum elements.
: @param $nodes Sequence of nodes from noteText.
: @param $sources Source documents.
: @param $editionHandle Edition handle.
: @param $volumeName Volume name.
: @param $pos Current position in recursion.
: @return Content with proper spacing.
:)
declare function local:buildNoteTextContent($nodes as node()*, $sources as node()*, $editionHandle as xs:string, $volumeName as xs:string, $pos as xs:integer) as item()* {
  if ($pos > count($nodes)) then
    ()
  else
    let $node := $nodes[$pos]
    let $nextNode := $nodes[$pos + 1]
    let $previousNode := $nodes[$pos - 1]
    let $isCurrentElement := $node/name() != ''
    let $isNextElement := $nextNode/name() != ''
    let $isNextTextNode := not($isNextElement) and $nextNode/string() != ''
    let $isPreviousElement := $previousNode/name() != ''
    let $currentOutput := switch ($node/name())
      case 'measures'
        return
          local:buildMeasures($node)
      case 'siglum'
        return
          local:buildSiglum($node, $sources, $editionHandle, $volumeName)
      case ('pitch')
        return
          local:buildPitch($node)
      case ('chord')
        return
          local:buildChord($node)
      case ('pitch-sequence')
        return
          local:buildSequence($node)
      case ('musicalSymbol')
        return
          if ($node/@glyph.uri) then
            local:buildSmufl($node/@glyph.uri)
          else
            ()
      case ('rend')
        return
          local:textRendition($node)
      default
        return
          let $nodeText := $node/string()
          let $trimmedText := if ($isPreviousElement and starts-with($nodeText, ' ')) then
            replace($nodeText, '^ +', ' ')
          else if ($isNextElement and $nodeText != '' and not(ends-with($nodeText, ' '))) then
            concat($nodeText, ' ')
          else
            $nodeText
          return
            $trimmedText
    return
      ($currentOutput,
      local:buildNoteTextContent($nodes, $sources, $editionHandle, $volumeName, $pos + 1))
};

(:~
: ###
: @param $measure-string ###.
: @param $siglum ###.
: @param $mdiv ###.
: @return ###
:)
declare function local:convertToMeasuresElement($measure-string as xs:string*, $siglum as xs:string*, $mdiv as xs:string*) as node()* {
  if (contains($measure-string, ',')) then
    (
    let $measure-substrings := tokenize($measure-string, ', ')
    let $tmp-measures := <measures>
      {
        for $item in $measure-substrings
        return
          <measure
            siglum="{$siglum}"
            mdiv="{$mdiv}"
            measure="{$item}"/>
      }</measures>
    return
      $tmp-measures
    )
  else
    (
    if (contains($measure-string, '–')) then
      (
      let $measures := tokenize($measure-string, '–')
      let $tmp-sequence := <measures><sequence
          siglum="{$siglum}"
          label-from="{$measures[1]}"
          label-to="{$measures[2]}"
          mdiv="{$mdiv}"/></measures>
      return
        $tmp-sequence
      )
    else
      (
      <measures><measure
          siglum="{$siglum}"
          mdiv="{$mdiv}"
          measure="{$measure-string}"/></measures>
      )
    )
};

(:~
: ###
: @param $sources ###
: @param $measures ###
: @return ###
:)
declare function local:populatePlist($sources as node()*, $measures as node(), $editionHandle as xs:string*) as xs:string* {
  for $sub-node in $measures/*
  return
    switch ($sub-node/name())
      case 'measure'
        return
          local:measureUri($sources, $sub-node, $editionHandle)
      case 'sequence'
        return
          string-join(for $m in (xs:integer($sub-node/@label-from/string()) to xs:integer($sub-node/@label-to/string()))
          return
            local:measureUri($sources, <measure
              siglum="{$sub-node/@siglum/string()}"
              mdiv="{$sub-node/@mdiv/string()}"
              label="{$m}"/>, $editionHandle), ' ')
      default
      return
        ""
};

(:~
: ###
: @param $sources ###
: @param $measure ###
: @return ###
:)
declare function local:measureUri($sources as node()*, $measure as node()*, $editionHandle as xs:string*) as xs:string* {
  let $url := "xmldb:exist:///db/apps/edirom-content/" || $editionHandle || "/sources/"
  let $sourceDoc := $sources//mei:mei[.//mei:identifier[text() = $measure/@siglum/string()]][1]
  return
    switch ($measure/name())
      case 'measure'
        return
          let $source-url := concat($url, replace(base-uri($sourceDoc), '^(.*/)(.*?)\.\w+$', '$2'))
          let $measure-id := $sourceDoc//mei:mdiv[substring-after(@label, 'Movement ') = $measure/@mdiv/string()]//mei:measure[@label/string() = $measure/@label/string()]/@xml:id/string()
          return
            concat($source-url, '#', $measure-id)
      case 'sequence'
        return
          '###ERROR###'
          (:let $source-url := concat($url, base-uri($sourceDoc)(:replace(base-uri($sourceDoc),'^(.*/)(.*?)\.\w+$','$2'):))
          for $measure-label in ($measure/@label-from, $measure/@label-to)
          return
            concat($source-url, '#', $sources//mei:mei[.//mei:identifier[text() = $measure/@siglum/string()]]//mei:mdiv[@n = $measure/@mdiv/string()]//mei:measure[@label = $measure-label]/@id/string()):)
      default
      return
        ''
};

declare function local:generate-uuid() as xs:string {
  let $rng := fn:random-number-generator()
  let $hex-chars := ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f')
  let $random-hex := function ($length as xs:integer) {
    string-join(for $i in 1 to $length
    return
      $hex-chars[xs:integer($rng('next')()('number') * 16) + 1], '')
  }
  let $pad := function ($str as xs:string, $length as xs:integer) {
    let $padding := string-join(for $i in 1 to ($length - string-length($str))
    return
      '0', '')
    return
      concat($padding, $str)
  }
  return
    concat(
    $pad($random-hex(8), 8), '-',
    $pad($random-hex(4), 4), '-',
    '4', $pad($random-hex(3), 3), '-',
    ('8', '9', 'a', 'b')[xs:integer($rng('next')()('number') * 4) + 1],
    $pad($random-hex(3), 3), '-',
    $pad($random-hex(12), 12)
    )
};

(: Paths and input documents :)
(: Adjust the collection Path to your local repository path :)

let $cnListNode := 
  if ($cnListFile != "") then
    doc($cnListFile)
  else
    parse-xml-fragment($cnList)
let $sources := collection($sourcesPath)

let $plist := map:merge(for $note in $cnListNode//criticalNote
return
  map:entry($note/@xml:id/string(), string-join(for $measures in $note/noteText//measures
  return
    local:populatePlist($sources, $measures, $editionHandle), ' '))
)
(:plist="{concat(local:populatePlist($sources, $note/measures/text()), ' ', map:get($plist, $note/@xml:id/string()))}":)
(: Build annots - return only inner annot elements without wrapper :)
let $criticalNotes :=
  for $note in $cnListNode//*:criticalNote
    let $mainSourcePlist := local:populatePlist($sources, local:convertToMeasuresElement(fn:string($note/*:measures/text()), $cnListNode/*:kb/@mainSource/string(), $cnListNode/*:kb/@n/string()), $editionHandle)
    (:      let $mainSourcePlist := "TEST":)
    let $titleText := 
      string-join(
        (
          if ($note/*:measures[normalize-space()]) then concat('T. ', $note/*:measures/normalize-space()) else (),
          if ($note/*:staff[normalize-space()]) then $note/*:staff/normalize-space() else (),
          if ($note/*:musicalEvent[normalize-space()]) then $note/*:musicalEvent/normalize-space() else ()
        )[. != ''],
        ' | '
      )
    return
      <annot
        xmlns="http://www.music-encoding.org/ns/mei"
        type="editorialComment"
        xml:id="{$note/@xml:id}"
        plist="{$mainSourcePlist, ' ', map:get($plist, $note/@xml:id/string())}"
      >
        <title
          lang="de">{
            let $title-measure := $note/*:measures/normalize-space()
            let $title-staff := $note/*:staff/normalize-space()
            let $title-text := $note/*:musicalEvent/normalize-space()
            return
              concat('T. ', $title-measure, ' | ', $title-staff, ' | ', $title-text)
          }</title>
        <p
          lang="de">{
            local:buildNoteTextContent($note/*:noteText/node(), $sources, $editionHandle, $volumeName, 1)
        }
      </p>
      <ptr
        type="priority"
        target="#criticalRemark"/>
      <ptr
        type="categories"
        target="{$note/*:categories/@values/data()}"/>
    </annot>

return
  $criticalNotes