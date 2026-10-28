<?xml version="1.0" encoding="UTF-8"?>
<!--
  Stylesheet: buildEdiromWorks.xsl
  Purpose:
    Rebuild the MEI work metadata for the EDIROM edition from a source FRBR
    structure. The stylesheet normalizes the work title, edition title, and
    work identifiers, and rewrites the work list so that it can be embedded in
    the generated edition output.

  Inputs:
    - A MEI document containing the work hierarchy and metadata.
    - Parameters: $annots, $workUUID, $workTitle, $editionTitle

  Output:
    - A transformed MEI document with normalized work metadata and notes
      statements for the EDIROM edition.
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:mei="http://www.music-encoding.org/ns/mei" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs mei" version="2.0">

  <xsl:output indent="yes"/>

  <!-- Optional annotation content used in the generated notesStmt block. -->
  <xsl:param name="annots" select="''" />
  <!-- Stable identifier for the generated work entry. -->
  <xsl:param name="workUUID" select="''" />
  <!-- Work title used for display in both language variants. -->
  <xsl:param name="workTitle" select="''" />
  <!-- Edition title inserted into the document metadata. -->
  <xsl:param name="editionTitle" select="''" />

  <!-- Root template: copy the MEI document and preserve all content except the
       explicitly rewritten work metadata. -->
  <xsl:template match="mei:mei">
    <mei:mei xmlns="http://www.music-encoding.org/ns/mei" xml:id="{$uuid[@name='editionWork']/text()}">
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </mei:mei>
  </xsl:template>

  <!-- Replace the work title with the edition-specific value supplied as a parameter. -->
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:titleStmt/mei:title">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$workTitle"/>
    </xsl:copy>
  </xsl:template>

  <!-- Replace the edition statement with the supplied edition title. -->
  <xsl:template match="/mei:mei/mei:meiHead/mei:fileDesc/mei:editionStmt/mei:edition">
    <xsl:copy>
      <xsl:copy-of select="@*"/>
      <xsl:value-of select="$editionTitle"/>
    </xsl:copy>
  </xsl:template>

  <!-- Rewrite the work element so that each edition-generated work gets a stable
       xml:id and inherits the remaining attributes and child nodes. -->
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work">
    <xsl:element name="work" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:attribute name="xml:id"><xsl:value-of select="$workUUID"/></xsl:attribute>
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()" />
    </xsl:element>
  </xsl:template>

  <!-- Emit the work title in both German and English language variants. -->
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work/mei:title">
    <xsl:element name="title" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:attribute name="xml:lang">de</xsl:attribute>
      <xsl:value-of select="$workTitle"/>
    </xsl:element>
    <xsl:element name="title" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:attribute name="xml:lang">en</xsl:attribute>
      <xsl:value-of select="$workTitle"/>
    </xsl:element>
  </xsl:template>

  <!-- Insert the notes statement supplied by the build process. -->
  <xsl:template match="/mei:mei/mei:meiHead/mei:workList/mei:work/mei:notesStmt">
    <xsl:element name="notesStmt" namespace="http://www.music-encoding.org/ns/mei">
      <xsl:copy-of select="$annots"/>
    </xsl:element>
  </xsl:template>

  <!-- Default identity copy rule for all remaining nodes and attributes. -->
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()" />
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>